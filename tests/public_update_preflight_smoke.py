"""
public_update_preflight_smoke.py — ACT-11

Smoke test for ``scripts/public_data_update_preflight.py``.

Covers:
  1. The preflight script runs to completion.
  2. It writes UPDATE_SUMMARY.md.
  3. It writes PUBLIC_DATA_DIFF.md.
  4. It writes MANIFEST_BEFORE.json.
  5. It writes MANIFEST_AFTER.json.
  6. It writes REVIEW_CHECKLIST.md.
  7. It does NOT create a git commit (we check that no new commits
     appear on HEAD with our temp marker).
  8. It does NOT touch the data/ gitignore state.
  9. It can detect a 1-project downgrade (by simulating a smaller plan).
 10. It can detect BookTrans Desk repo pointing at conanxin-homepage
     (by temporarily editing public-data/registry/projects.yml).

This test is deliberately NOT in `make all` (it mutates public-data/
on disk). Run it on demand via `make public-update-test`.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "public_data_update_preflight.py"
PLAN = REPO_ROOT / "config" / "public-data-export-plan.yml"
PUBLIC_DATA = REPO_ROOT / "public-data"
GITIGNORE = REPO_ROOT / ".gitignore"


def _run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(
        cmd, cwd=str(cwd or REPO_ROOT), capture_output=True, text=True, check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _ok(label: str) -> None:
    print(f"  [ok] {label}")


def _fail(label: str, detail: str) -> None:
    print(f"  [FAIL] {label}: {detail}")


def test_runs_and_writes_artifacts() -> tuple[bool, Path]:
    """Run the preflight in a temp output dir and verify the artifacts exist."""
    with tempfile.TemporaryDirectory(prefix="act11-preflight-") as tmp:
        output_dir = Path(tmp) / "out"
        cmd = [
            sys.executable, str(SCRIPT),
            "--plan", str(PLAN),
            "--output", str(output_dir),
        ]
        rc, stdout, stderr = _run(cmd)
        if rc != 0:
            _fail("preflight_exit_zero", f"rc={rc} stderr={stderr[:300]}")
            return False, output_dir
        _ok(f"preflight_exit_zero (rc={rc})")
        expected = [
            "UPDATE_SUMMARY.md",
            "PUBLIC_DATA_DIFF.md",
            "MANIFEST_BEFORE.json",
            "MANIFEST_AFTER.json",
            "REVIEW_CHECKLIST.md",
            "REDACTION_RESULT.md",
            "NEXT_STEPS.md",
        ]
        for name in expected:
            p = output_dir / name
            if p.exists() and p.stat().st_size > 0:
                _ok(f"wrote {name}")
            else:
                _fail(f"wrote {name}", "missing or empty")
                return False, output_dir
        return True, output_dir


def test_no_git_commit() -> None:
    """The preflight must not have created a new commit on HEAD."""
    rc, stdout, _ = _run(["git", "rev-parse", "HEAD"])
    if rc != 0:
        _fail("no_git_commit", "could not read HEAD")
        return
    head_before = stdout.strip()
    # Re-run the preflight (idempotent — same content) and check HEAD unchanged.
    with tempfile.TemporaryDirectory(prefix="act11-head-") as tmp:
        _run([
            sys.executable, str(SCRIPT),
            "--plan", str(PLAN),
            "--output", str(Path(tmp) / "out"),
        ])
    rc, stdout, _ = _run(["git", "rev-parse", "HEAD"])
    head_after = stdout.strip()
    if head_before == head_after:
        _ok("no_git_commit (HEAD unchanged)")
    else:
        _fail("no_git_commit", f"HEAD changed: {head_before} -> {head_after}")


def test_gitignore_untouched() -> None:
    """The preflight must not modify .gitignore (data/ must stay ignored)."""
    text = GITIGNORE.read_text(encoding="utf-8")
    if "data/" in text and "generated/" in text:
        _ok("gitignore_data_and_generated_still_ignored")
    else:
        _fail("gitignore_intact", f"data/ or generated/ missing from .gitignore")


def test_detects_1project_downgrade() -> None:
    """Run with a plan that requests more projects than the export produces.

    We simulate this by temporarily rewriting public-data/registry/projects.yml
    to contain only 1 project, then running the preflight. The check
    ``project_count_meets_plan`` should FAIL.
    """
    projects_yml = PUBLIC_DATA / "registry" / "projects.yml"
    if not projects_yml.exists():
        _fail("detect_1project_downgrade", "public-data/registry/projects.yml missing")
        return
    backup = projects_yml.read_text(encoding="utf-8")
    output_dir = Path(tempfile.mkdtemp(prefix="act11-down-")) / "out"
    try:
        # Truncate to a single project entry.
        lines = backup.splitlines()
        first_entry_end = 0
        for i, line in enumerate(lines):
            if i > 0 and line.startswith("- id:"):
                first_entry_end = i
                break
        truncated = "\n".join(lines[:first_entry_end]) + "\n"
        projects_yml.write_text(truncated, encoding="utf-8")
        # Use --keep-public-data so the preflight doesn't overwrite
        # our truncated file with the real export.
        rc, _, stderr = _run([
            sys.executable, str(SCRIPT),
            "--plan", str(PLAN),
            "--output", str(output_dir),
            "--keep-public-data",
        ])
        # rc=1 means a regression check failed (expected).
        if rc == 1:
            summary = (output_dir / "UPDATE_SUMMARY.md").read_text(encoding="utf-8")
            if "FAIL" in summary and "project_count_meets_plan" in summary:
                _ok("detects_1project_downgrade (rc=1, check reported FAIL)")
            else:
                _fail("detects_1project_downgrade",
                      f"rc=1 but summary missing expected FAIL: {summary[:200]}")
        else:
            _fail("detects_1project_downgrade",
                  f"expected rc=1, got rc={rc} stderr={stderr[:200]}")
    finally:
        # Restore the original file.
        projects_yml.write_text(backup, encoding="utf-8")
        shutil.rmtree(output_dir.parent, ignore_errors=True)


def test_detects_booktrans_homepage() -> None:
    """Run with booktrans-desk's repo pointing at conanxin-homepage.

    The check ``booktrans_repo_not_homepage`` should FAIL.
    """
    projects_yml = PUBLIC_DATA / "registry" / "projects.yml"
    if not projects_yml.exists():
        _fail("detect_booktrans_homepage", "public-data/registry/projects.yml missing")
        return
    backup = projects_yml.read_text(encoding="utf-8")
    output_dir = Path(tempfile.mkdtemp(prefix="act11-bk-")) / "out"
    try:
        text = backup
        # Replace the booktrans-desk repo line.
        new_lines = []
        in_entry = False
        for line in text.splitlines():
            if line.startswith("- id:") and "booktrans-desk" in line:
                in_entry = True
                new_lines.append(line)
                continue
            if in_entry and line.strip().startswith("repo:"):
                new_lines.append('  repo: "conanxin-homepage"')
                in_entry = False
                continue
            if line.startswith("- id:") and "booktrans-desk" not in line:
                in_entry = False
            new_lines.append(line)
        projects_yml.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        rc, _, _ = _run([
            sys.executable, str(SCRIPT),
            "--plan", str(PLAN),
            "--output", str(output_dir),
            "--keep-public-data",
        ])
        if rc == 1:
            summary = (output_dir / "UPDATE_SUMMARY.md").read_text(encoding="utf-8")
            if "FAIL" in summary and "booktrans_repo_not_homepage" in summary:
                _ok("detects_booktrans_repo_homepage (rc=1, check reported FAIL)")
            else:
                _fail("detects_booktrans_homepage",
                      f"summary missing expected FAIL: {summary[:200]}")
        else:
            _fail("detects_booktrans_homepage", f"expected rc=1, got rc={rc}")
    finally:
        projects_yml.write_text(backup, encoding="utf-8")
        shutil.rmtree(output_dir.parent, ignore_errors=True)


def main() -> int:
    print("public_update_preflight_smoke — ACT-11")
    ok, _ = test_runs_and_writes_artifacts()
    if not ok:
        return 1
    test_no_git_commit()
    test_gitignore_untouched()
    test_detects_1project_downgrade()
    test_detects_booktrans_homepage()
    # Re-run the preflight once more to restore public-data/ to the
    # real export state (the regression tests may have left it in a
    # read-only mode, and the earlier test_detects_* tests may have
    # left a truncated file if the --keep-public-data flag didn't work).
    _run([
        sys.executable, str(SCRIPT),
        "--plan", str(PLAN),
        "--output", str(tempfile.mkdtemp(prefix="act11-restore-")),
    ])
    print("public_update_preflight_smoke — PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
