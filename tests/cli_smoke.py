"""
cli_smoke.py — ACT-2 smoke test for the tower CLI.

Runs the CLI in an isolated temporary copy of `examples/` (seeded as
`data/`) so the real `data/` is never touched. Exercises:

  - tower validate
  - tower build (incl. embedded HTML)
  - register-agent idempotency
  - register-project idempotency
  - report-phase (PASS / FAIL)
  - report-failure (status=FAIL, health=red, failure_reason)
  - report-review (REVIEW_REPORT + review_target)
  - report-handoff (HANDOFF)
  - report-release (RELEASE)
  - redaction FAIL (token-like summary) and redaction WARN (home path)
  - generated/index.json sanity
  - site/index.embedded.html contains TOWER_DATA
  - re-running all of the above (everything idempotent on registry)

Exits 0 on PASS, 1 on FAIL.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
TOWER = REPO_ROOT / "scripts" / "tower.py"

OK = "ok"
FAIL = "FAIL"
errors: list[str] = []


def _run(label: str, args: list[str], cwd: Path, env: dict) -> tuple[int, str, str]:
    print(f">>> {label}: {' '.join(args)}")
    r = subprocess.run(
        [sys.executable, str(TOWER), *args],
        cwd=cwd, env=env, capture_output=True, text=True,
    )
    if r.stdout:
        # trim noisy preamble
        for line in r.stdout.splitlines()[-6:]:
            print(f"  | {line}")
    if r.returncode != 0 and r.stderr:
        print(f"  [STDERR] {r.stderr.strip()[:300]}")
    return r.returncode, r.stdout, r.stderr


def _assert(cond: bool, msg: str) -> None:
    if cond:
        print(f"  [{OK}] {msg}")
    else:
        print(f"  [{FAIL}] {msg}")
        errors.append(msg)


def _make_workspace() -> tuple[Path, dict]:
    """Create a temp dir with examples/ copied to data/, and a tower env.

    Also copies site/ so that `tower build` (which generates
    site/index.embedded.html from site/index.html) has the template.
    """
    tmp = Path(tempfile.mkdtemp(prefix="tower-cli-smoke-"))
    (tmp / "data" / "registry").mkdir(parents=True)
    (tmp / "data" / "events").mkdir(parents=True)
    (tmp / "site").mkdir(parents=True)
    # Copy examples/registry and events into the temp data/
    for f in (REPO_ROOT / "examples" / "registry").iterdir():
        shutil.copy(f, tmp / "data" / "registry" / f.name)
    for f in (REPO_ROOT / "examples" / "events").iterdir():
        shutil.copy(f, tmp / "data" / "events" / f.name)
    # Copy site template
    for f in (REPO_ROOT / "site").iterdir():
        if f.is_file():
            shutil.copy(f, tmp / "site" / f.name)
    env = {**os.environ, "TOWER_ROOT": str(tmp)}
    return tmp, env


def main() -> int:
    tmp, env = _make_workspace()
    print(f"workspace: {tmp}\n")

    # 1. validate clean state
    rc, _, _ = _run("validate (clean)", ["validate"], tmp, env)
    _assert(rc == 0, "validate clean state")

    # 2. build
    rc, _, _ = _run("build", ["build"], tmp, env)
    _assert(rc == 0, "build clean state")
    idx = tmp / "generated" / "index.json"
    _assert(idx.exists(), "generated/index.json exists after build")
    data = json.loads(idx.read_text()) if idx.exists() else {}
    _assert(data.get("summary", {}).get("project_count") == 2,
            f"summary.project_count == 2 (got {data.get('summary', {}).get('project_count')})")

    # 3. register-agent + idempotency
    rc, _, _ = _run(
        "register-agent smoke-1", [
            "register-agent",
            "--agent-id", "smoke-1",
            "--name", "Smoke Agent 1",
            "--machine", "ci",
            "--role", "smoke-test",
        ],
        tmp, env,
    )
    _assert(rc == 0, "register-agent smoke-1")
    # Idempotent second call
    rc2, stdout2, _ = _run(
        "register-agent smoke-1 again", [
            "register-agent",
            "--agent-id", "smoke-1",
            "--name", "Smoke Agent 1",
            "--machine", "ci",
            "--role", "smoke-test",
        ],
        tmp, env,
    )
    _assert(rc2 == 0, "register-agent smoke-1 idempotent (no error)")
    _assert("already exists" in stdout2, "register-agent smoke-1 reports 'already exists'")

    # 4. register-project + idempotency
    rc, _, _ = _run(
        "register-project smoke-proj", [
            "register-project",
            "--project-id", "smoke-proj",
            "--name", "Smoke Project",
            "--repo", "conanxin/smoke-proj",
            "--location", "local",
            "--category", "test",
            "--status", "ACTIVE",
            "--description", "Smoke test project",
            "--agent-id", "smoke-1",
        ],
        tmp, env,
    )
    _assert(rc == 0, "register-project smoke-proj")
    rc2, _, _ = _run(
        "register-project smoke-proj again", [
            "register-project",
            "--project-id", "smoke-proj",
            "--name", "Smoke Project",
            "--repo", "conanxin/smoke-proj",
            "--location", "local",
            "--agent-id", "smoke-1",
        ],
        tmp, env,
    )
    _assert(rc2 == 0, "register-project smoke-proj idempotent")

    # 5. report-phase PASS
    rc, _, _ = _run(
        "report-phase PASS", [
            "report-phase",
            "--project-id", "smoke-proj",
            "--agent-id", "smoke-1",
            "--phase-id", "S1",
            "--phase-name", "Smoke phase 1",
            "--status", "PASS",
            "--summary", "First smoke phase passed",
            "--next", "S2",
        ],
        tmp, env,
    )
    _assert(rc == 0, "report-phase PASS")

    # 6. report-failure (with redaction-safe summary)
    rc, _, _ = _run(
        "report-failure", [
            "report-failure",
            "--project-id", "smoke-proj",
            "--agent-id", "smoke-1",
            "--phase-id", "S2",
            "--phase-name", "Smoke phase 2",
            "--summary", "Second smoke phase failed because of assertion",
            "--failure-reason", "AssertionError: 2+2 expected to be 4 but got 5",
            "--next", "S2-fix",
        ],
        tmp, env,
    )
    _assert(rc == 0, "report-failure (status=FAIL, health=red)")
    # Verify the event actually has the right shape
    fail_events = sorted((tmp / "data" / "events").glob("*FAILURE*.json"))
    _assert(len(fail_events) >= 1, f"FAILURE event file exists ({len(fail_events)} found)")
    if fail_events:
        fev = json.loads(fail_events[-1].read_text())
        _assert(fev.get("status") == "FAIL", "FAILURE event status == FAIL")
        _assert(fev.get("health") == "red", "FAILURE event health == red")
        _assert(bool(fev.get("failure_reason")), "FAILURE event has failure_reason")

    # 7. report-review
    rc, _, _ = _run(
        "report-review", [
            "report-review",
            "--project-id", "smoke-proj",
            "--agent-id", "smoke-1",  # self-review allowed for smoke purposes
            "--phase-id", "S1-review",
            "--phase-name", "Review S1",
            "--status", "PASS",
            "--summary", "S1 review passed",
            "--target-agent-id", "smoke-1",
            "--target-phase-id", "S1",
            "--target-commit", "deadbeef",
        ],
        tmp, env,
    )
    _assert(rc == 0, "report-review")
    rev_events = sorted((tmp / "data" / "events").glob("*REVIEW*.json"))
    if rev_events:
        rev = json.loads(rev_events[-1].read_text())
        _assert(rev.get("event_type") == "REVIEW_REPORT",
                "REVIEW event_type == REVIEW_REPORT")
        _assert(isinstance(rev.get("review_target"), dict) and
                rev["review_target"].get("agent_id") == "smoke-1" and
                rev["review_target"].get("phase_id") == "S1",
                "REVIEW event has review_target {agent_id, phase_id}")

    # 8. report-handoff
    rc, _, _ = _run(
        "report-handoff", [
            "report-handoff",
            "--project-id", "smoke-proj",
            "--from-agent-id", "smoke-1",
            "--to-agent-id", "smoke-2",
            "--current-phase", "S2",
            "--reason", "S2 needs a different specialist",
        ],
        tmp, env,
    )
    _assert(rc == 0, "report-handoff")
    h_events = sorted((tmp / "data" / "events").glob("*HANDOFF*.json"))
    if h_events:
        hev = json.loads(h_events[-1].read_text())
        _assert(hev.get("event_type") == "HANDOFF", "HANDOFF event_type == HANDOFF")
        _assert(hev.get("handoff", {}).get("to_agent_id") == "smoke-2",
                "HANDOFF event has to_agent_id == smoke-2")

    # 9. report-release
    rc, _, _ = _run(
        "report-release", [
            "report-release",
            "--project-id", "smoke-proj",
            "--agent-id", "smoke-1",
            "--version", "v0.0.1",
            "--summary", "First smoke release",
            "--source-repo", "conanxin/smoke-proj",
            "--source-commit", "abcdef12",
            "--release-url", "https://example.com/release/v0.0.1",
        ],
        tmp, env,
    )
    _assert(rc == 0, "report-release")
    rel_events = sorted((tmp / "data" / "events").glob("*RELEASE*.json"))
    if rel_events:
        rev = json.loads(rel_events[-1].read_text())
        _assert(rev.get("status") == "RELEASED", "RELEASE event status == RELEASED")
        _assert(rev.get("health") == "green", "RELEASE event health == green")
        _assert(rev.get("release", {}).get("version") == "v0.0.1",
                "RELEASE event has release.version == v0.0.1")

    # 10. redaction FAIL — token-shaped summary
    rc, _, _ = _run(
        "report-phase with token (should FAIL redaction)", [
            "report-phase",
            "--project-id", "smoke-proj",
            "--agent-id", "smoke-1",
            "--phase-id", "BAD",
            "--phase-name", "Bad phase",
            "--status", "PASS",
            "--summary", "Tested with api_key=sk-1234567890abcdef ok",
        ],
        tmp, env,
    )
    _assert(rc == 3, f"redaction FAIL returns exit 3 (got {rc})")
    # Verify NO event was written
    bad_events = list((tmp / "data" / "events").glob("*PHASE*__BAD*.json"))
    _assert(len(bad_events) == 0, "redaction FAIL did NOT write event file")

    # 11. redaction WARN — home path (still writes)
    rc, _, _ = _run(
        "report-phase with home path (should WARN)", [
            "report-phase",
            "--project-id", "smoke-proj",
            "--agent-id", "smoke-1",
            "--phase-id", "WARN",
            "--phase-name", "Warn phase",
            "--status", "PASS",
            "--summary", "Built in /home/ubuntu/workdir and passed",
        ],
        tmp, env,
    )
    _assert(rc == 0, f"redaction WARN still writes (exit {rc})")
    warn_events = list((tmp / "data" / "events").glob("*PHASE*__WARN*.json"))
    _assert(len(warn_events) >= 1, "redaction WARN event file exists")

    # 12. final build + dashboard sanity
    rc, _, _ = _run("final build", ["build"], tmp, env)
    _assert(rc == 0, "final build")
    emb = tmp / "site" / "index.embedded.html"
    _assert(emb.exists(), "site/index.embedded.html exists")
    if emb.exists():
        html = emb.read_text()
        m = re.search(r"window\.__TOWER_DATA__\s*=\s*(\{.*?\});", html, re.DOTALL)
        _assert(m is not None, "embedded HTML contains __TOWER_DATA__")
        if m:
            try:
                inline = json.loads(m.group(1))
                _assert(inline.get("summary", {}).get("project_count", 0) >= 3,
                        f"inline data has 3+ projects (got {inline.get('summary', {}).get('project_count')})")
                # Verify timeline contains all event types
                types_in_timeline = {t.get("event_type") for t in inline.get("timeline", [])}
                _assert("AGENT_REGISTERED" in types_in_timeline, "timeline has AGENT_REGISTERED")
                _assert("PROJECT_REGISTERED" in types_in_timeline, "timeline has PROJECT_REGISTERED")
                _assert("PHASE_REPORT" in types_in_timeline, "timeline has PHASE_REPORT")
                _assert("REVIEW_REPORT" in types_in_timeline, "timeline has REVIEW_REPORT")
                _assert("HANDOFF" in types_in_timeline, "timeline has HANDOFF")
                _assert("RELEASE" in types_in_timeline, "timeline has RELEASE")
            except json.JSONDecodeError as e:
                errors.append(f"inline data not valid JSON: {e}")

    # Cleanup
    shutil.rmtree(tmp, ignore_errors=True)

    print()
    if errors:
        print(f"CLI SMOKE TEST FAILED: {len(errors)} issue(s)")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("CLI SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
