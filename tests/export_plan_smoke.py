"""
export_plan_smoke.py — ACT-9C smoke test for the public-data export plan.

The plan file (``config/public-data-export-plan.yml``) is the single
source of truth for what the public dashboard is allowed to show. ACT-9C
adds ``--plan`` support to both ``export_public_data.py`` and
``build_public_data_candidate.py``, and this test pins the contract:

  1. config/public-data-export-plan.yml exists
  2. plan's `projects` list contains at least 3 real projects
  3. export_public_data.py --plan can produce a public snapshot
  4. build_public_data_candidate.py --plan can produce a candidate
  5. plan matches the MANIFEST.json project_filter
  6. make publish-preflight does NOT silently degrade to 1 project
  7. mixing --plan and --project-id is a hard error
  8. plan file does not contain forbidden patterns (local absolute
     paths, /Users/, IP addresses, tokens, .env references)

Exit codes:
  0  PASS
  1  FAIL
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLAN_PATH = REPO / "config" / "public-data-export-plan.yml"
EXPORT_SCRIPT = REPO / "scripts" / "export_public_data.py"
CANDIDATE_SCRIPT = REPO / "scripts" / "build_public_data_candidate.py"
PUBLIC_DATA = REPO / "public-data"

# Patterns that MUST NOT appear in the plan file. A hit means the
# plan is leaking the kind of info that belongs in data/ (which is
# gitignored) or in private env vars — exactly what the plan is
# supposed to NOT contain.
#
# Note: we strip YAML comments (lines starting with `#`, after
# stripping leading whitespace) before scanning, so the plan can
# use the same words in its own documentation ("this file must
# not contain /home/..." etc.) without tripping the check. We
# only scan the YAML *values*.
FORBIDDEN_PATTERNS: tuple[tuple[str, str], ...] = (
    # Real /home/<user>/... paths have real-looking body segments
    # (letters, digits, hyphens, underscores), not "..." or ")" etc.
    (r"/home/[A-Za-z][A-Za-z0-9_\-]{2,}/[A-Za-z0-9_\-/.]+",
     "local /home/<user>/ absolute path"),
    (r"/Users/[A-Za-z][A-Za-z0-9_\-]{2,}/[A-Za-z0-9_\-/.]+",
     "macOS /Users/<user>/ absolute path"),
    (r"/mnt/[a-z]/[A-Za-z][A-Za-z0-9_\-]{2,}/[A-Za-z0-9_\-/.]+",
     "WSL /mnt/<drive>/ absolute path"),
    (r"\b\d{1,3}(?:\.\d{1,3}){3}\b", "IPv4 address"),
    (r"(?i)token\s*=\s*[A-Za-z0-9_\-]{8,}", "literal token= assignment"),
    (r"(?i)api[_-]?key\s*[=:]\s*[A-Za-z0-9_\-]{8,}", "literal API key"),
    (r"(?i)Bearer\s+[A-Za-z0-9_\-\.]{8,}", "Bearer authorization header"),
    (r"\.env\b", "reference to .env file"),
)


def _strip_yaml_comments(raw: str) -> str:
    """Return plan text with YAML comments removed. Comments are
    lines starting with ``#`` (after optional leading whitespace),
    and ``#`` mid-line is treated as start of comment for the
    value side. This is a best-effort stripper; it does not
    preserve quoting nuances."""
    out: list[str] = []
    for line in raw.splitlines():
        # Whole-line comment?
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        # Mid-line comment: find a # that's not inside quotes.
        # Cheap heuristic: split on the first ' #' or '\t#'.
        cut = -1
        in_s = False
        in_d = False
        for i, ch in enumerate(line):
            if ch == "'" and not in_d:
                in_s = not in_s
            elif ch == '"' and not in_s:
                in_d = not in_d
            elif ch == "#" and not in_s and not in_d \
                    and (i == 0 or line[i-1] in " \t"):
                cut = i
                break
        if cut >= 0:
            line = line[:cut].rstrip()
        out.append(line)
    return "\n".join(out)


def _check(label: str, ok: bool, detail: str = "") -> bool:
    flag = "PASS" if ok else "FAIL"
    print(f"  [{flag}] {label}" + (f" — {detail}" if detail else ""))
    return ok


def _load_plan() -> dict:
    """Load the plan YAML using whichever loader is available
    (yaml_mini or PyYAML). Mirrors what the scripts do."""
    try:
        from yaml_mini import load as _load  # type: ignore
    except Exception:
        import yaml  # type: ignore
        def _load(p: Path):
            return yaml.safe_load(p.read_text(encoding="utf-8"))
    return _load(PLAN_PATH)  # type: ignore[arg-type]


def test_plan_exists() -> bool:
    print("test_plan_exists")
    if not _check("plan file exists", PLAN_PATH.exists(),
                  f"path={PLAN_PATH}"):
        return False
    return True


def test_plan_has_at_least_3_projects(plan: dict) -> bool:
    print("test_plan_has_at_least_3_projects")
    projects = plan.get("projects", [])
    if not _check("plan has `projects:` list", isinstance(projects, list)
                  and len(projects) >= 3,
                  f"got {len(projects) if isinstance(projects, list) else 'NOT-A-LIST'}"):
        return False
    for p in ("agent-project-control-tower", "artvee-gallery", "booktrans-desk"):
        if not _check(f"plan includes {p}", p in projects):
            return False
    return True


def test_export_with_plan(tmp: Path, plan: dict) -> bool:
    print("test_export_with_plan")
    out = tmp / "pd"
    proc = subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT),
         "--plan", str(PLAN_PATH),
         "--output", str(out),
         "--replace"],
        capture_output=True, text=True,
    )
    if not _check("exit 0", proc.returncode == 0,
                  f"rc={proc.returncode}\nstdout={proc.stdout}\nstderr={proc.stderr}"):
        return False
    manifest_path = out / "MANIFEST.json"
    if not _check("MANIFEST.json written", manifest_path.exists()):
        return False
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not _check("MANIFEST.plan_file is set", m.get("plan_file") is not None,
                  f"plan_file={m.get('plan_file')}"):
        return False
    if not _check("MANIFEST.plan_name matches", m.get("plan_name") == "default-public-dashboard"):
        return False
    if not _check("MANIFEST.project_filter is the plan's project list",
                  m.get("project_filter") is not None
                  and len(m.get("project_filter", [])) == len(plan.get("projects", [])),
                  f"project_filter={m.get('project_filter')}"):
        return False
    return True


def test_candidate_with_plan(tmp: Path, plan: dict) -> bool:
    print("test_candidate_with_plan")
    if not (REPO / "data").exists():
        print("  [SKIP] data/ not present; using examples")
        source = "examples"
    else:
        source = "data"
    out = tmp / "cand"
    proc = subprocess.run(
        [sys.executable, str(CANDIDATE_SCRIPT),
         "--plan", str(PLAN_PATH),
         "--source", source,
         "--output", str(out)],
        capture_output=True, text=True,
    )
    if not _check("exit 0", proc.returncode == 0,
                  f"rc={proc.returncode}\nstdout={proc.stdout}\nstderr={proc.stderr}"):
        return False
    summary_path = out / "reports" / "CANDIDATE_SUMMARY.md"
    if not _check("CANDIDATE_SUMMARY.md exists", summary_path.exists()):
        return False
    summary = summary_path.read_text(encoding="utf-8")
    if not _check("summary mentions plan file path",
                  str(PLAN_PATH) in summary):
        return False
    if not _check("summary mentions plan.name",
                  "default-public-dashboard" in summary):
        return False
    if not _check("summary lists plan projects",
                  "agent-project-control-tower" in summary
                  and "artvee-gallery" in summary
                  and "booktrans-desk" in summary):
        return False
    manifest = json.loads((out / "MANIFEST.json").read_text(encoding="utf-8"))
    plan_projects = plan.get("projects", [])
    if not _check("candidate MANIFEST.project_filter is the plan list",
                  manifest.get("project_filter") is not None
                  and len(manifest["project_filter"]) == len(plan_projects)):
        return False
    return True


def test_plan_matches_manifest(plan: dict) -> bool:
    print("test_plan_matches_manifest")
    # The plan in this checkout should match the public-data MANIFEST
    # only if public-data was just refreshed. We don't require a
    # match here (public-data may be one phase behind plan edits),
    # but the public-data MANIFEST MUST be a SUBSET (or equal) of
    # the plan's project list. This guards against the historical
    # bug where public-data silently held 1 project while the plan
    # intended 3.
    manifest_path = PUBLIC_DATA / "MANIFEST.json"
    if not manifest_path.exists():
        print("  [SKIP] public-data/MANIFEST.json missing")
        return True
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    pub_filter = set(m.get("project_filter") or [])
    plan_projects = set(plan.get("projects", []))
    extra = pub_filter - plan_projects
    if not _check("public-data project_filter ⊆ plan.projects (no extra)",
                  not extra, f"extra={extra}"):
        return False
    return True


def test_publish_preflight_does_not_degrade() -> bool:
    print("test_publish_preflight_does_not_degrade")
    if not (REPO / "data").exists():
        print("  [SKIP] data/ not present")
        return True
    proc = subprocess.run(
        ["make", "publish-preflight"],
        cwd=str(REPO), capture_output=True, text=True,
    )
    if not _check("make publish-preflight exit 0", proc.returncode == 0,
                  f"rc={proc.returncode}\nstderr={proc.stderr[-500:]}"):
        return False
    # Look for the "n projects, n agents, n events" line in stdout
    m = re.search(
        r"(\d+) projects?, (\d+) agents?, (\d+) events?",
        proc.stdout,
    )
    if not _check("publish-preflight prints a counts line", m is not None,
                  "(no counts line found in stdout)"):
        return False
    if m is None:
        return False
    n_projects = int(m.group(1))
    n_agents = int(m.group(2))
    n_events = int(m.group(3))
    if not _check("publish-preflight result has >=3 projects (not 1)",
                  n_projects >= 3, f"got {n_projects}"):
        return False
    if not _check("publish-preflight result has >=2 agents",
                  n_agents >= 2, f"got {n_agents}"):
        return False
    if not _check("publish-preflight result has >=21 events",
                  n_events >= 21, f"got {n_events}"):
        return False
    return True


def test_mutual_exclusion_export() -> bool:
    print("test_mutual_exclusion_export")
    proc = subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT),
         "--plan", str(PLAN_PATH),
         "--project-id", "agent-project-control-tower"],
        capture_output=True, text=True,
    )
    if not _check("--plan + --project-id fails (export)", proc.returncode == 2,
                  f"rc={proc.returncode}\nstderr={proc.stderr}"):
        return False
    if not _check("error message mentions mutual exclusion",
                  "mutually exclusive" in proc.stderr.lower()
                  or "mutually exclusive" in proc.stdout.lower()):
        return False
    return True


def test_mutual_exclusion_candidate() -> bool:
    print("test_mutual_exclusion_candidate")
    proc = subprocess.run(
        [sys.executable, str(CANDIDATE_SCRIPT),
         "--plan", str(PLAN_PATH),
         "--source", "examples",
         "--project-id", "agent-project-control-tower"],
        capture_output=True, text=True,
    )
    if not _check("--plan + --project-id fails (candidate)", proc.returncode == 2,
                  f"rc={proc.returncode}\nstderr={proc.stderr}"):
        return False
    return True


def test_plan_no_forbidden_patterns(plan_raw: str) -> bool:
    print("test_plan_no_forbidden_patterns")
    # Strip YAML comments so the plan's own documentation can
    # mention the patterns it's guarding against.
    stripped = _strip_yaml_comments(plan_raw)
    ok = True
    for pattern, label in FORBIDDEN_PATTERNS:
        hits = re.findall(pattern, stripped)
        if not _check(f"no {label}", not hits,
                      f"hits={hits[:3]}" if hits else ""):
            ok = False
    return ok


def main() -> int:
    # Plan file existence is a precondition for everything else.
    if not PLAN_PATH.exists():
        print(f"FAIL: plan file missing: {PLAN_PATH}")
        return 1
    plan_raw = PLAN_PATH.read_text(encoding="utf-8")
    try:
        plan = _load_plan()
    except Exception as e:
        print(f"FAIL: cannot parse plan YAML: {e}")
        return 1

    with tempfile.TemporaryDirectory(prefix="act9c-export-plan-smoke-") as td:
        tmp = Path(td)
        results = [
            test_plan_exists(),
            test_plan_has_at_least_3_projects(plan),
            test_export_with_plan(tmp, plan),
            test_candidate_with_plan(tmp, plan),
            test_plan_matches_manifest(plan),
            test_publish_preflight_does_not_degrade(),
            test_mutual_exclusion_export(),
            test_mutual_exclusion_candidate(),
            test_plan_no_forbidden_patterns(plan_raw),
        ]

    print()
    if all(results):
        print("export_plan_smoke — PASS")
        return 0
    print("export_plan_smoke — FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
