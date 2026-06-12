"""
candidate_artifact_smoke.py — ACT-9B smoke test for
``scripts/build_public_data_candidate.py``.

Coverage (mapped to the ACT-9B brief):

  1. ``--source public-data`` produces a candidate directory
  2. ``--source examples`` produces a candidate directory
  3. candidate does NOT contain ``data/`` or ``generated/``
  4. ``CANDIDATE_SUMMARY.md`` exists
  5. ``MANIFEST_DIFF.md`` exists
  6. ``REDACTION_REPORT.md`` exists
  7. ``REVIEW_CHECKLIST.md`` exists
  8. ``public-data-candidate.tar.gz`` exists and extracts
  9. tarball does NOT contain ``data/``, ``generated/``,
     ``.git``, ``node_modules``, ``.env``
 10. ``--source data`` requested but ``data/`` missing → exit 2

Exit codes:
  0  PASS
  1  FAIL
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "build_public_data_candidate.py"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True,
    )


def _check(label: str, ok: bool, detail: str = "") -> bool:
    flag = "PASS" if ok else "FAIL"
    print(f"  [{flag}] {label}" + (f" — {detail}" if detail else ""))
    return ok


def test_source_public_data(tmp: Path) -> bool:
    print("test_source_public_data")
    out = tmp / "pd"
    proc = _run(
        "--source", "public-data",
        "--output", str(out),
    )
    if not _check("exit 0", proc.returncode == 0, f"rc={proc.returncode}"):
        print(proc.stdout); print(proc.stderr)
        return False
    if not _check("CANDIDATE_SUMMARY.md exists",
                  (out / "reports" / "CANDIDATE_SUMMARY.md").exists()):
        return False
    if not _check("MANIFEST_DIFF.md exists",
                  (out / "reports" / "MANIFEST_DIFF.md").exists()):
        return False
    if not _check("REDACTION_REPORT.md exists",
                  (out / "reports" / "REDACTION_REPORT.md").exists()):
        return False
    if not _check("REVIEW_CHECKLIST.md exists",
                  (out / "reports" / "REVIEW_CHECKLIST.md").exists()):
        return False
    if not _check("tarball exists",
                  (out / "public-data-candidate.tar.gz").exists()):
        return False
    if not _check("no data/ in candidate", not (out / "data").exists()):
        return False
    if not _check("no generated/ in candidate", not (out / "generated").exists()):
        return False
    tarball = out / "public-data-candidate.tar.gz"
    with tarfile.open(tarball, "r:gz") as tf:
        members = tf.getnames()
    bad = [m for m in members if any(
        seg in m.split("/") for seg in (
            "data", "generated", ".git", "node_modules", ".env",
        )
    )]
    if not _check("tarball excludes forbidden paths", not bad, f"bad={bad}"):
        return False
    if not _check("tarball has registry/",
                  any("registry/" in m for m in members)):
        return False
    if not _check("tarball has events/",
                  any("events/" in m for m in members)):
        return False
    if not _check("tarball has reports/",
                  any("reports/" in m for m in members)):
        return False
    return True


def test_source_examples(tmp: Path) -> bool:
    print("test_source_examples")
    out = tmp / "ex"
    proc = _run(
        "--source", "examples",
        "--output", str(out),
    )
    if not _check("exit 0", proc.returncode == 0,
                  f"rc={proc.returncode}\nstdout={proc.stdout}\nstderr={proc.stderr}"):
        return False
    if not _check("CANDIDATE_SUMMARY.md exists",
                  (out / "reports" / "CANDIDATE_SUMMARY.md").exists()):
        return False
    summary = (out / "reports" / "CANDIDATE_SUMMARY.md").read_text(encoding="utf-8")
    if not _check("summary mentions FIXTURE", "FIXTURE" in summary,
                  "summary must mark fixture mode"):
        return False
    if not _check("tarball exists",
                  (out / "public-data-candidate.tar.gz").exists()):
        return False
    return True


def test_source_data_present(tmp: Path) -> bool:
    print("test_source_data_present")
    if not (REPO / "data").exists():
        print("  [SKIP] data/ not present (CI-like); skipping")
        return True
    out = tmp / "data"
    proc = _run(
        "--source", "data",
        "--output", str(out),
        "--project-id", "agent-project-control-tower",
        "--project-id", "artvee-gallery",
        "--project-id", "booktrans-desk",
    )
    if not _check("exit 0", proc.returncode == 0,
                  f"rc={proc.returncode}\n{proc.stderr}"):
        return False
    summary = (out / "reports" / "CANDIDATE_SUMMARY.md").read_text(encoding="utf-8")
    if not _check("summary marks real data mode", "LOCAL GITIGNORED" in summary):
        return False
    return True


def test_source_data_missing(tmp: Path) -> bool:
    print("test_source_data_missing")
    fake_repo = tmp / "fake-repo"
    fake_scripts = fake_repo / "scripts"
    fake_lib = fake_scripts / "lib"
    fake_scripts.mkdir(parents=True)
    fake_lib.mkdir(parents=True)
    shutil.copy(str(SCRIPT),
                str(fake_scripts / "build_public_data_candidate.py"))
    real_lib = REPO / "scripts" / "lib"
    shutil.copy(str(real_lib / "redaction.py"),
                str(fake_lib / "redaction.py"))
    shutil.copy(str(real_lib / "yaml_mini.py"),
                str(fake_lib / "yaml_mini.py"))
    shutil.copy(str(real_lib / "__init__.py"),
                str(fake_lib / "__init__.py"))
    out = tmp / "missing"
    proc = subprocess.run(
        [sys.executable,
         str(fake_scripts / "build_public_data_candidate.py"),
         "--source", "data", "--output", str(out)],
        capture_output=True, text=True,
    )
    if not _check("exit 2 on missing data/", proc.returncode == 2,
                  f"rc={proc.returncode}\n{proc.stderr}"):
        return False
    if not _check("error mentions data/", "data/" in proc.stderr):
        return False
    if not _check("error mentions GitHub Actions", "GitHub Actions" in proc.stderr):
        return False
    return True


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="act9b-cand-smoke-") as td:
        tmp = Path(td)
        results = [
            test_source_public_data(tmp),
            test_source_examples(tmp),
            test_source_data_present(tmp),
            test_source_data_missing(tmp),
        ]
    print()
    if all(results):
        print("candidate_artifact_smoke — PASS")
        return 0
    print("candidate_artifact_smoke — FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
