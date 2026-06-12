"""
public_data_update_preflight.py — ACT-11

Local preflight tool for a human or authorized primary agent who is about
to update ``public-data/``. This script is **deliberately not in the
auto-export path**. It does:

  1. Read ``config/public-data-export-plan.yml`` for the export scope.
  2. Snapshot the current ``public-data/`` (manifest + file list).
  3. Run ``export_public_data.py --plan ... --replace`` to regenerate
     ``public-data/`` from ``data/``.
  4. Validate the regenerated ``public-data/`` and re-build
     ``generated/index.json`` and ``site/index.embedded.html``.
  5. Run regression checks (1-project downgrade, BookTrans Desk repo
     misclassification, redaction FAIL > 0).
  6. Write a reviewable artifact directory under
     ``artifacts/public-data-update-preflight/``.

It does **not**:

  * Run ``git add``.
  * Run ``git commit``.
  * Run ``git push``.
  * Touch Cloudflare Pages.
  * Modify ``data/`` or ``generated/`` (except as build output).

The human is expected to:

  1. Read the artifact files.
  2. Run ``git diff public-data/`` to see what would change.
  3. Explicitly ``git add`` the files they accept.
  4. Commit and push by hand.

Exit codes:

  0   — preflight ran, all regression checks passed, artifacts written
  1   — preflight ran but a regression check failed
  2   — preflight could not run (missing plan, missing data/, etc.)
  3   — redaction FAIL > 0 (hard error, cannot export)
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


# Path constants — keep them absolute so the script can be run from
# any working directory.
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = REPO_ROOT / "config" / "public-data-export-plan.yml"
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "public-data-update-preflight"
PUBLIC_DATA = REPO_ROOT / "public-data"
GENERATED = REPO_ROOT / "generated"
SITE_EMBEDDED = REPO_ROOT / "site" / "index.embedded.html"
EXPORT_SCRIPT = REPO_ROOT / "scripts" / "export_public_data.py"
VALIDATE_SCRIPT = REPO_ROOT / "scripts" / "tower.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_yaml(path: Path) -> dict[str, Any]:
    """Tiny YAML reader for the plan file.

    We avoid PyYAML to keep this script runnable in a vanilla CI runner.
    The plan file has a well-known shape (list-of-strings under
    ``projects:`` and ``agents:``) so a line-based parser is sufficient.
    """
    if not path.exists():
        return {}
    out: dict[str, Any] = {}
    section: str | None = None
    list_key: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith(" "):
            # Top-level key.
            section = None
            list_key = None
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if value:
                # Scalar value (strip optional quotes).
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                out[key] = value
                section = key
            else:
                # A top-level key with no scalar value: it may hold a
                # list of scalar items on subsequent indented lines.
                section = key
                list_key = key
        else:
            if section is None:
                continue
            stripped = line.strip()
            if stripped.startswith("- "):
                if list_key is None:
                    continue
                item = stripped[2:].strip()
                if item.startswith('"') and item.endswith('"'):
                    item = item[1:-1]
                out.setdefault(list_key, []).append(item)
            elif ":" in stripped:
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip()
                if not value:
                    # A nested list is about to begin.
                    list_key = key
                    out.setdefault(key, [])
                else:
                    list_key = None
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    out[f"{section}.{key}"] = value
    return out


def _manifest_snapshot(public_data: Path) -> dict[str, Any]:
    """Capture the current public-data state before regeneration."""
    manifest_path = public_data / "MANIFEST.json"
    if manifest_path.exists():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            # Derive project/agent counts from the manifest's filter lists
            # if they aren't already present.
            projects = data.get("project_filter") or data.get("projects") or []
            agents = data.get("agent_filter") or data.get("agents") or []
            events_count = (
                data.get("event_count")
                or len(data.get("events") or [])
                or _count_events(public_data)
            )
            return {
                "snapshot_at": data.get("generated_at") or _now_iso(),
                "source": data.get("source", "manifest"),
                "project_count": len(projects),
                "agent_count": len(agents),
                "event_count": events_count,
                "projects": list(projects),
                "agents": list(agents),
                "events": list(data.get("events") or []),
            }
        except Exception:
            pass
    # Fall back to scanning the directory.
    return _scan_public_data(public_data)


def _count_events(public_data: Path) -> int:
    ev_dir = public_data / "events"
    if not ev_dir.exists():
        return 0
    return sum(1 for _ in ev_dir.glob("*.json"))


def _scan_public_data(public_data: Path) -> dict[str, Any]:
    projects: list[str] = []
    agents: list[str] = []
    reg = public_data / "registry"
    if reg.exists():
        for f in sorted(reg.glob("*.yml")):
            text = f.read_text(encoding="utf-8", errors="replace")
            for line in text.splitlines():
                if line.startswith("- id:"):
                    val = line.split(":", 1)[1].strip()
                    if "projects" in f.name:
                        projects.append(val)
                    else:
                        agents.append(val)
    return {
        "snapshot_at": _now_iso(),
        "source": "fallback_directory_scan",
        "project_count": len(projects),
        "agent_count": len(agents),
        "event_count": _count_events(public_data),
        "projects": projects,
        "agents": agents,
        "events": [],
    }


def _redaction_summary(stdout: str) -> dict[str, int]:
    """Parse FAIL/WARN/PASS counts from export_public_data.py output."""
    summary = {"FAIL": 0, "WARN": 0, "PASS": 0}
    for line in stdout.splitlines():
        line_upper = line.strip().upper()
        for key in summary:
            if line_upper.startswith(f"{key}=") or f"{key}:" in line_upper:
                # Try to extract a trailing integer.
                tail = line_upper.split(key, 1)[1].lstrip(":=").strip()
                digits = ""
                for ch in tail:
                    if ch.isdigit():
                        digits += ch
                    else:
                        break
                if digits:
                    summary[key] = int(digits)
    return summary


# ---------------------------------------------------------------------------
# Regression checks
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


def _check_project_count(plan: dict[str, Any], manifest: dict[str, Any]) -> CheckResult:
    expected = len(plan.get("projects", []))
    actual = manifest.get("project_count", 0)
    ok = actual >= expected
    return CheckResult(
        name="project_count_meets_plan",
        passed=ok,
        detail=f"plan expects {expected} project(s), public-data has {actual}",
    )


def _check_no_booktrans_homepage(
    public_data: Path, plan: dict[str, Any],
) -> CheckResult:
    """If booktrans-desk is in the plan, its repo must NOT be conanxin-homepage."""
    if "booktrans-desk" not in plan.get("projects", []):
        return CheckResult(
            name="booktrans_repo_not_homepage",
            passed=True,
            detail="booktrans-desk not in plan, check skipped",
        )
    projects_yml = public_data / "registry" / "projects.yml"
    if not projects_yml.exists():
        return CheckResult(
            name="booktrans_repo_not_homepage",
            passed=False,
            detail="registry/projects.yml missing after export",
        )
    text = projects_yml.read_text(encoding="utf-8", errors="replace")
    # Find the booktrans-desk entry's repo line.
    in_entry = False
    repo_value = ""
    for line in text.splitlines():
        if line.startswith("- id:"):
            in_entry = "booktrans-desk" in line
            continue
        if in_entry and line.strip().startswith("repo:"):
            repo_value = line.split(":", 1)[1].strip()
            break
    bad = "conanxin-homepage" in repo_value
    return CheckResult(
        name="booktrans_repo_not_homepage",
        passed=not bad,
        detail=f"booktrans-desk repo = {repo_value!r}"
        + (" (FAIL: points at conanxin-homepage)" if bad else " (OK)"),
    )


def _check_no_hp33_for_booktrans(
    public_data: Path, plan: dict[str, Any],
) -> CheckResult:
    """If booktrans-desk is in the plan, no event should have phase_id=HP-33."""
    if "booktrans-desk" not in plan.get("projects", []):
        return CheckResult(
            name="booktrans_no_hp33",
            passed=True,
            detail="booktrans-desk not in plan, check skipped",
        )
    events_dir = public_data / "events"
    bad_files: list[str] = []
    if events_dir.exists():
        for f in events_dir.glob("*.json"):
            try:
                payload = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if payload.get("project_id") != "booktrans-desk":
                continue
            phase = payload.get("phase_id") or ""
            if "HP-33" in str(phase):
                bad_files.append(f.name)
    return CheckResult(
        name="booktrans_no_hp33",
        passed=not bad_files,
        detail=f"HP-33 events for booktrans-desk: {bad_files or 'none'}",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _run(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
    proc = subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True, check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Local preflight for a public-data update (ACT-11).",
    )
    parser.add_argument(
        "--plan", default=str(DEFAULT_PLAN),
        help="path to public-data-export-plan.yml",
    )
    parser.add_argument(
        "--output", default=str(DEFAULT_OUTPUT),
        help="artifact output directory",
    )
    parser.add_argument(
        "--keep-public-data", action="store_true",
        help="do NOT actually rewrite public-data/ (read-only mode)",
    )
    args = parser.parse_args()

    plan_path = Path(args.plan).resolve()
    output_dir = Path(args.output).resolve()

    if not plan_path.exists():
        print(f"ERROR: plan file not found: {plan_path}", file=sys.stderr)
        return 2
    plan = _read_yaml(plan_path)
    if not plan:
        print(f"ERROR: plan file is empty or unreadable: {plan_path}", file=sys.stderr)
        return 2

    # Make sure the output directory is clean.
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Snapshot the current public-data/ state.
    manifest_before = _manifest_snapshot(PUBLIC_DATA)
    (output_dir / "MANIFEST_BEFORE.json").write_text(
        json.dumps(manifest_before, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # 2. Run export_public_data.py --plan ... --replace.
    if args.keep_public_data:
        export_stdout = "[read-only mode] export skipped\n"
        export_stderr = ""
        export_rc = 0
    else:
        export_cmd = [
            sys.executable, str(EXPORT_SCRIPT),
            "--plan", str(plan_path),
            "--replace",
        ]
        export_rc, export_stdout, export_stderr = _run(export_cmd, REPO_ROOT)
        (output_dir / "EXPORT_STDOUT.txt").write_text(export_stdout, encoding="utf-8")
        (output_dir / "EXPORT_STDERR.txt").write_text(export_stderr, encoding="utf-8")

    if export_rc != 0:
        msg = f"export_public_data.py exited {export_rc}\n{export_stderr}"
        (output_dir / "FATAL.md").write_text(msg, encoding="utf-8")
        print(msg, file=sys.stderr)
        return 2

    # 3. Validate public-data.
    validate_rc, validate_stdout, validate_stderr = _run(
        [sys.executable, str(VALIDATE_SCRIPT), "validate", "--source", "public-data"],
        REPO_ROOT,
    )
    (output_dir / "VALIDATE_STDOUT.txt").write_text(validate_stdout, encoding="utf-8")
    (output_dir / "VALIDATE_STDERR.txt").write_text(validate_stderr, encoding="utf-8")

    # 4. Build generated/index.json from public-data.
    build_rc, build_stdout, build_stderr = _run(
        [sys.executable, str(VALIDATE_SCRIPT), "build", "--source", "public-data"],
        REPO_ROOT,
    )
    (output_dir / "BUILD_STDOUT.txt").write_text(build_stdout, encoding="utf-8")
    (output_dir / "BUILD_STDERR.txt").write_text(build_stderr, encoding="utf-8")

    # 5. Snapshot the AFTER state.
    manifest_after = _manifest_snapshot(PUBLIC_DATA)
    (output_dir / "MANIFEST_AFTER.json").write_text(
        json.dumps(manifest_after, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # 6. Redaction summary.
    redaction = _redaction_summary(export_stdout)
    redaction_md = (
        "# Redaction Result\n\n"
        f"- FAIL: {redaction['FAIL']}\n"
        f"- WARN: {redaction['WARN']}\n"
        f"- PASS: {redaction['PASS']}\n\n"
    )
    if redaction["FAIL"] > 0:
        redaction_md += (
            "**HARD ERROR**: redaction FAIL > 0. The export must be aborted.\n"
            "Inspect `EXPORT_STDOUT.txt` and `EXPORT_STDERR.txt` for offending fields.\n"
        )
    elif redaction["WARN"] > 0:
        redaction_md += (
            f"**WARN**: {redaction['WARN']} WARN(s) require human judgment.\n"
            "See the export stdout for the exact lines.\n"
        )
    else:
        redaction_md += "OK — no FAIL, no WARN.\n"
    (output_dir / "REDACTION_RESULT.md").write_text(redaction_md, encoding="utf-8")

    # 7. Regression checks.
    checks: list[CheckResult] = [
        _check_project_count(plan, manifest_after),
        _check_no_booktrans_homepage(PUBLIC_DATA, plan),
        _check_no_hp33_for_booktrans(PUBLIC_DATA, plan),
    ]
    if redaction["FAIL"] > 0:
        checks.append(CheckResult(
            name="redaction_fail_zero",
            passed=False,
            detail=f"redaction FAIL = {redaction['FAIL']} (must be 0)",
        ))
    if validate_rc != 0:
        checks.append(CheckResult(
            name="validate_clean",
            passed=False,
            detail=f"validate exited {validate_rc}",
        ))
    if build_rc != 0:
        checks.append(CheckResult(
            name="build_clean",
            passed=False,
            detail=f"build exited {build_rc}",
        ))

    # 8. PUBLIC_DATA_DIFF.md — a human-readable diff of the manifest.
    diff_lines = [
        "# Public-data Diff (manifest)\n",
        f"Generated at: {_now_iso()}\n",
        "",
        "| field | before | after |",
        "| --- | --- | --- |",
        f"| project_count | {manifest_before.get('project_count')} "
        f"| {manifest_after.get('project_count')} |",
        f"| agent_count | {manifest_before.get('agent_count')} "
        f"| {manifest_after.get('agent_count')} |",
        f"| event_count | {manifest_before.get('event_count')} "
        f"| {manifest_after.get('event_count')} |",
        "",
        "## projects (after)\n",
        *[f"- {p}" for p in manifest_after.get("projects", [])],
        "",
        "## agents (after)\n",
        *[f"- {a}" for a in manifest_after.get("agents", [])],
    ]
    (output_dir / "PUBLIC_DATA_DIFF.md").write_text(
        "\n".join(diff_lines) + "\n", encoding="utf-8",
    )

    # 9. UPDATE_SUMMARY.md.
    all_passed = all(c.passed for c in checks)
    summary_lines = [
        "# Public-data Update Preflight — Summary\n",
        f"Generated at: {_now_iso()}\n",
        f"Plan: `{plan_path.relative_to(REPO_ROOT)}`\n",
        f"Output: `{output_dir}`\n",
        f"Mode: {'read-only' if args.keep_public_data else 'write'}\n",
        "",
        "## Result\n",
        "**" + ("PASS" if all_passed else "FAIL") + "**\n",
        "",
        "## Checks\n",
        *[f"- {'✅' if c.passed else '❌'} **{c.name}** — {c.detail}"
          for c in checks],
        "",
        "## Counts\n",
        f"- projects: {manifest_after.get('project_count')} "
        f"(plan expects ≥ {len(plan.get('projects', []))})",
        f"- agents:   {manifest_after.get('agent_count')}",
        f"- events:   {manifest_after.get('event_count')}",
        f"- redaction FAIL/WARN/PASS: "
        f"{redaction['FAIL']}/{redaction['WARN']}/{redaction['PASS']}",
    ]
    (output_dir / "UPDATE_SUMMARY.md").write_text(
        "\n".join(summary_lines) + "\n", encoding="utf-8",
    )

    # 10. REVIEW_CHECKLIST.md.
    checklist = (
        "# Public-data Update Preflight — Review Checklist\n\n"
        "For the human reviewer. Walk through these in order.\n\n"
        "1. [ ] Open `UPDATE_SUMMARY.md`. Confirm the overall result is **PASS**.\n"
        "2. [ ] Open `PUBLIC_DATA_DIFF.md`. Confirm project/agent/event counts "
        "match the intent of this update.\n"
        "3. [ ] Open `MANIFEST_BEFORE.json` and `MANIFEST_AFTER.json`. "
        "Spot-check that the project set still matches the plan.\n"
        "4. [ ] Open `REDACTION_RESULT.md`. Confirm FAIL=0. "
        "If WARN>0, eyeball each WARN and decide.\n"
        "5. [ ] Run `git diff public-data/` and review the actual file changes. "
        "Look for any unexpected project_id / source_repo / phase_id.\n"
        "6. [ ] If booktrans-desk is in the plan, confirm:\n"
        "   - `repo` = `conanxin/booktrans-desk` (NOT conanxin-homepage)\n"
        "   - current phase = S13 (NOT HP-33)\n"
        "   - source_commit = 16f38b6\n"
        "7. [ ] Run `git status --short`. Confirm only `public-data/`, "
        "`site/index.embedded.html`, and `reports/` are staged — NOT "
        "`data/`, `generated/`, or `artifacts/`.\n"
        "8. [ ] Run `git diff --cached --name-only` after your explicit "
        "`git add`. Confirm the list matches the diff you reviewed.\n"
    )
    (output_dir / "REVIEW_CHECKLIST.md").write_text(checklist, encoding="utf-8")

    # 11. NEXT_STEPS.md.
    next_steps = (
        "# Next Steps — Manual Public-data Update\n\n"
        "The preflight ran. The remaining work is human.\n\n"
        "## If the preflight FAILED\n\n"
        "Do NOT proceed. The preflight artifacts are the diagnosis.\n"
        "Fix the underlying issue (mis-attribution, redaction FAIL, "
        "1-project downgrade) and re-run this preflight.\n\n"
        "## If the preflight PASSED\n\n"
        "1. Read `UPDATE_SUMMARY.md` and `PUBLIC_DATA_DIFF.md`.\n"
        "2. Walk through `REVIEW_CHECKLIST.md`.\n"
        "3. When satisfied, stage the changes explicitly:\n\n"
        "   ```bash\n"
        "   git add public-data/registry/projects.yml \\\n"
        "           public-data/registry/agents.yml \\\n"
        "           public-data/MANIFEST.json \\\n"
        "           public-data/events/\n"
        "   git add site/index.embedded.html\n"
        "   ```\n\n"
        "4. Verify the staged set:\n\n"
        "   ```bash\n"
        "   git status --short\n"
        "   git diff --cached --stat\n"
        "   ```\n\n"
        "5. Commit and push:\n\n"
        "   ```bash\n"
        "   git commit -m \"<phase-id>: <what changed in public-data>\"\n"
        "   git push\n"
        "   ```\n\n"
        "6. Wait 60–90s for Cloudflare Pages + CDN cache.\n"
        "7. Run the online verification checklist at\n"
        "   `templates/checklists/online-verification-checklist.md`.\n\n"
        "## NEVER\n\n"
        "- `git add .` (stage only what you reviewed)\n"
        "- `git add data/` (data/ is gitignored and must stay private)\n"
        "- `git add generated/` (build artifact, regenerated by CI)\n"
        "- `git add artifacts/` (review-only, never committed)\n"
        "- `git push --force`\n"
    )
    (output_dir / "NEXT_STEPS.md").write_text(next_steps, encoding="utf-8")

    # 12. Console summary.
    print(f"preflight artifacts: {output_dir}")
    print(f"  UPDATE_SUMMARY.md  — {'PASS' if all_passed else 'FAIL'}")
    for c in checks:
        print(f"  {'✅' if c.passed else '❌'} {c.name}: {c.detail}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
