"""
tests/smoke.py — minimal smoke test for ACT-1.

Runs the full pipeline (validate → build → embedded site) and asserts the
generated output matches the ACT-1 acceptance criteria:

  - 2 projects in index.json
  - 3 agents in index.json
  - 3 events in index.json
  - local-book-tool current_status == FAIL (latest event is L2 FAIL)
  - local-book-tool current_health == red
  - cloud-art-site current_status == PASS
  - cloud-art-site current_health == green
  - site/index.embedded.html exists and contains the inline data

Exits 0 on PASS, non-zero on any failure.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
INDEX_JSON = ROOT / "generated" / "index.json"
EMBEDDED_HTML = ROOT / "site" / "index.embedded.html"

OK = "\033[32mok\033[0m"
FAIL = "\033[31mFAIL\033[0m"
errors: list[str] = []


def _run(label: str, cmd: list[str]) -> bool:
    print(f"\n>>> {label}: {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    print(r.stdout, end="")
    if r.returncode != 0:
        print(f"  [{FAIL}] {label} exited with {r.returncode}")
        print(r.stderr, end="")
        errors.append(f"{label} failed")
        return False
    print(f"  [{OK}] {label}")
    return True


def _assert(cond: bool, msg: str) -> None:
    if cond:
        print(f"  [{OK}] {msg}")
    else:
        print(f"  [{FAIL}] {msg}")
        errors.append(msg)


def main() -> int:
    # Re-run the pipeline so we test the current state, not a stale artifact.
    ok = True
    ok &= _run("validate", ["python", "scripts/validate_examples.py"])
    ok &= _run("build",    ["python", "scripts/build_index.py"])
    ok &= _run("site",     ["python", "scripts/build_embedded_site.py"])
    if not ok:
        return 1

    print("\n=== Acceptance checks ===")
    if not INDEX_JSON.exists():
        errors.append(f"missing {INDEX_JSON}")
        return 1
    data = json.loads(INDEX_JSON.read_text())

    _assert(data["summary"]["project_count"] == 2,
            f"summary.project_count == 2 (got {data['summary']['project_count']})")
    _assert(data["summary"]["agent_count"] == 3,
            f"summary.agent_count == 3 (got {data['summary']['agent_count']})")
    _assert(data["summary"]["event_count"] == 3,
            f"summary.event_count == 3 (got {data['summary']['event_count']})")

    projects = {p["project_id"]: p for p in data["projects"]}
    lbt = projects.get("local-book-tool", {})
    cas = projects.get("cloud-art-site", {})

    _assert(lbt.get("current_status") == "FAIL",
            f"local-book-tool current_status == FAIL (got {lbt.get('current_status')})")
    _assert(lbt.get("current_health") == "red",
            f"local-book-tool current_health == red (got {lbt.get('current_health')})")
    _assert(lbt.get("current_phase_id") == "L2",
            f"local-book-tool current_phase_id == L2 (got {lbt.get('current_phase_id')})")
    _assert(lbt.get("last_agent_id") == "local-codex",
            f"local-book-tool last_agent_id == local-codex (got {lbt.get('last_agent_id')})")
    _assert(lbt.get("event_count") == 2,
            f"local-book-tool event_count == 2 (got {lbt.get('event_count')})")

    _assert(cas.get("current_status") == "PASS",
            f"cloud-art-site current_status == PASS (got {cas.get('current_status')})")
    _assert(cas.get("current_health") == "green",
            f"cloud-art-site current_health == green (got {cas.get('current_health')})")
    _assert(cas.get("event_count") == 1,
            f"cloud-art-site event_count == 1 (got {cas.get('event_count')})")

    # Timeline ordering: newest first
    times = [t.get("created_at") or "" for t in data["timeline"]]
    _assert(times == sorted(times, reverse=True),
            f"timeline is sorted newest-first")

    # Embedded HTML must exist and contain the data
    if not EMBEDDED_HTML.exists():
        errors.append(f"missing {EMBEDDED_HTML}")
    else:
        html = EMBEDDED_HTML.read_text()
        m = re.search(r"window\.__TOWER_DATA__\s*=\s*(\{.*?\});", html, re.DOTALL)
        _assert(m is not None, "embedded HTML contains __TOWER_DATA__ block")
        if m:
            try:
                inline = json.loads(m.group(1))
                _assert(inline.get("summary", {}).get("project_count") == 2,
                        "inline data summary.project_count == 2")
            except json.JSONDecodeError as e:
                errors.append(f"inline data not valid JSON: {e}")

    print()
    if errors:
        print(f"SMOKE TEST FAILED: {len(errors)} issue(s)")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
