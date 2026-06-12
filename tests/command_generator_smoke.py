"""
command_generator_smoke.py — ACT-7B smoke test for the command
generator and the template/CLI alignment checker.

Coverage (mapped to the ACT-7B brief):

  1. report-phase generates a single-line command
  2. report-review refuses --source-repo / --source-commit /
     --design-reason / --impact-analysis
  3. export-public-data emits all --project-id in declared order
  4. values with spaces and apostrophes are correctly shlex-quoted
  5. unknown subcommand returns non-zero (FAIL with no output)
  6. generated output contains no '\\n' or '\\\\' continuations
  7. check_template_cli_alignment.py returns 0 on the real templates
  8. check_template_cli_alignment.py returns 1 when a template
     gains a forbidden flag (proves the checker is real, not a
     no-op)

Exit codes:
  0  PASS
  1  FAIL
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
GEN = REPO_ROOT / "scripts" / "generate_tower_command.py"
ALIGN = REPO_ROOT / "scripts" / "check_template_cli_alignment.py"

OK = "ok"
errors: list[str] = []


def _run(args: list[str]) -> tuple[int, str, str]:
    r = subprocess.run(
        [sys.executable, str(GEN), *args],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    return r.returncode, r.stdout, r.stderr


def _ok(label: str) -> None:
    print(f"  [{OK}] {label}")


def _fail(label: str, detail: str = "") -> None:
    msg = f"  [FAIL] {label}"
    if detail:
        msg += f" :: {detail}"
    print(msg)
    errors.append(label)


# ---------------------------------------------------------------- tests


def test_1_report_phase_single_line() -> None:
    code, out, err = _run([
        "report-phase",
        "--project-id", "booktrans-desk",
        "--agent-id",   "local-hermes",
        "--phase-id",   "S13",
        "--phase-name", "Blocker Fixes and Manual Validation Rerun",
        "--status",     "PARTIAL",
        "--health",     "amber",
        "--summary",    "S13 blocker fixes complete; automated PASS, click-through BLOCKED_MANUAL.",
        "--source-repo","conanxin/booktrans-desk",
        "--source-commit", "16f38b6",
        "--next",       "Schedule real-user click-through before S14.",
    ])
    if code != 0:
        _fail("test_1_report_phase_single_line: non-zero exit", err)
        return
    if "\n" in out.rstrip("\n"):
        _fail("test_1_report_phase_single_line: output contains newline",
              repr(out))
        return
    if "\\" in out:
        _fail("test_1_report_phase_single_line: output contains backslash continuation",
              repr(out))
        return
    if "report-phase" not in out or "--project-id booktrans-desk" not in out:
        _fail("test_1_report_phase_single_line: missing subcommand or flag",
              repr(out))
        return
    _ok("test_1_report_phase_single_line")


def test_2_report_review_rejects_unsupported_flags() -> None:
    # The four known-bad flags for report-review.
    for bad in ("--source-repo", "--source-commit",
                "--design-reason", "--impact-analysis"):
        code, out, err = _run([
            "report-review",
            "--project-id",      "agent-project-control-tower",
            "--agent-id",        "cloud-openclaw",
            "--phase-id",        "ACT-8-review",
            "--status",          "PASS",
            "--summary",         "x",
            "--target-agent-id", "local-hermes",
            "--target-phase-id", "ACT-7",
            bad,                 "some-value",
        ])
        if code == 0:
            _fail(f"test_2_report_review_rejects_unsupported_flags: "
                  f"generator ACCEPTED {bad} on report-review",
                  repr(out))
            return
        if "is NOT a valid flag" not in err and \
           "is NOT a valid flag" not in out:
            _fail(f"test_2_report_review_rejects_unsupported_flags: "
                  f"wrong error message for {bad}",
                  err + " | " + out)
            return
    _ok("test_2_report_review_rejects_unsupported_flags")


def test_3_export_public_data_multi_project_id() -> None:
    code, out, err = _run([
        "export-public-data",
        "--source",      "data",
        "--output",      "public-data",
        "--project-id",  "agent-project-control-tower",
        "--project-id",  "artvee-gallery",
        "--project-id",  "booktrans-desk",
        "--replace",
    ])
    if code != 0:
        _fail("test_3_export_public_data_multi_project_id: non-zero exit",
              err)
        return
    # The three --project-id must all appear, in the order given.
    p1 = out.find("agent-project-control-tower")
    p2 = out.find("artvee-gallery")
    p3 = out.find("booktrans-desk")
    if not (0 < p1 < p2 < p3):
        _fail("test_3_export_public_data_multi_project_id: "
              "order mismatch",
              repr(out))
        return
    if "\n" in out.rstrip("\n"):
        _fail("test_3_export_public_data_multi_project_id: output not single-line",
              repr(out))
        return
    _ok("test_3_export_public_data_multi_project_id")


def test_4_shlex_quote_for_values_with_spaces() -> None:
    code, out, err = _run([
        "report-phase",
        "--project-id", "booktrans-desk",
        "--agent-id",   "local-hermes",
        "--phase-id",   "S13",
        "--status",     "PASS",
        "--summary",    "It is a 'quoted' string with spaces.",
    ])
    if code != 0:
        _fail("test_4_shlex_quote_for_values_with_spaces: non-zero exit",
              err)
        return
    # shlex.quote wraps the value in single quotes and escapes
    # embedded apostrophes using the bash idiom: close-'-escape-'-
    # reopen ('"'"'). Either of these acceptable forms passes:
    #   'It is a '"'"'quoted'"'"' string with spaces.'
    #   "It is a 'quoted' string with spaces."  (no apostrophe escape)
    # We just verify the literal --summary substring is NOT present
    # unquoted (which would break bash), and the output remains a
    # single line.
    if "It is a 'quoted' string with spaces." in out:
        _fail("test_4_shlex_quote_for_values_with_spaces: "
              "value appears unquoted in output (would break bash)",
              repr(out))
        return
    if "\n" in out.rstrip("\n"):
        _fail("test_4_shlex_quote_for_values_with_spaces: "
              "output is not single-line",
              repr(out))
        return
    # The quoted form must contain the literal substrings of the
    # original value, possibly with quoting noise around them.
    for token in ("It is a", "quoted", "string with spaces."):
        if token not in out:
            _fail("test_4_shlex_quote_for_values_with_spaces: "
                  f"token {token!r} not in output",
                  repr(out))
            return
    _ok("test_4_shlex_quote_for_values_with_spaces")


def test_5_unknown_subcommand_returns_nonzero() -> None:
    code, out, err = _run(["register-recipe", "--x", "y"])
    if code == 0:
        _fail("test_5_unknown_subcommand_returns_nonzero: exit was 0",
              out + " | " + err)
        return
    if "unknown subcommand" not in err:
        _fail("test_5_unknown_subcommand_returns_nonzero: "
              "missing 'unknown subcommand' in stderr",
              err)
        return
    _ok("test_5_unknown_subcommand_returns_nonzero")


def test_6_no_newline_no_continuation_in_output() -> None:
    # Stress: 8 flags, mix of str + bool + append.
    code, out, err = _run([
        "report-phase",
        "--project-id", "p",
        "--agent-id",   "a",
        "--phase-id",   "ph",
        "--status",     "PASS",
        "--summary",    "ok",
        "--next",       "first",
        "--next",       "second",
        "--source-repo",    "o/r",
        "--source-commit",  "abcdef0",
    ])
    if code != 0:
        _fail("test_6_no_newline_no_continuation_in_output: non-zero exit",
              err)
        return
    if "\n" in out.rstrip("\n"):
        _fail("test_6_no_newline_no_continuation_in_output: newline present",
              repr(out))
        return
    if "\\\\" in out:
        _fail("test_6_no_newline_no_continuation_in_output: "
              "backslash continuation present",
              repr(out))
        return
    if out.count("--next") != 2:
        _fail("test_6_no_newline_no_continuation_in_output: "
              "--next append did not emit twice",
              repr(out))
        return
    _ok("test_6_no_newline_no_continuation_in_output")


def test_7_alignment_checker_passes_on_real_templates() -> None:
    r = subprocess.run(
        [sys.executable, str(ALIGN)],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    if r.returncode != 0:
        _fail("test_7_alignment_checker_passes_on_real_templates: "
              f"non-zero exit ({r.returncode})",
              r.stdout + " | " + r.stderr)
        return
    if "PASS" not in r.stdout:
        _fail("test_7_alignment_checker_passes_on_real_templates: "
              "missing PASS line in output",
              r.stdout)
        return
    _ok("test_7_alignment_checker_passes_on_real_templates")


def test_8_alignment_checker_catches_drift() -> None:
    """Inject a forbidden flag into a temporary copy of report-review.txt
    and verify the checker refuses to pass. This proves the checker
    is doing real work, not always returning 0."""
    src = REPO_ROOT / "templates" / "telegram" / "report-review.txt"
    if not src.is_file():
        _fail("test_8_alignment_checker_catches_drift: "
              "real report-review.txt not found",
              str(src))
        return

    with tempfile.TemporaryDirectory() as td:
        tmp_dir = Path(td) / "templates" / "telegram"
        tmp_dir.mkdir(parents=True)
        # Copy all real templates except report-review.txt
        real_dir = REPO_ROOT / "templates" / "telegram"
        for f in real_dir.glob("*.txt"):
            if f.name == "report-review.txt":
                continue
            (tmp_dir / f.name).write_text(f.read_text(encoding="utf-8"),
                                          encoding="utf-8")
        # Now write a poisoned report-review.txt with --source-repo
        # inside its Command: block (which the checker WILL inspect).
        poisoned = (
            "Poisoned template for ACT-7B smoke test.\n"
            "\n"
            "Command:\n"
            "\n"
            "  python scripts/tower.py report-review \\\n"
            "    --project-id p \\\n"
            "    --source-repo conanxin/foo \\\n"
            "    --agent-id a \\\n"
            "    --phase-id ph \\\n"
            "    --status PASS \\\n"
            "    --summary s \\\n"
            "    --target-agent-id ta \\\n"
            "    --target-phase-id tp\n"
        )
        (tmp_dir / "report-review.txt").write_text(poisoned,
                                                   encoding="utf-8")

        # Invoke the checker with a monkey-patched TEMPLATES_DIR.
        # The checker uses a hard-coded REPO_ROOT path, so the
        # cleanest way is to import the module and override its
        # module-level constant. importlib.util is stdlib only.
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "align_under_test", str(ALIGN))
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        setattr(mod, "TEMPLATES_DIR", tmp_dir)
        code = mod.main()
        if code == 0:
            _fail("test_8_alignment_checker_catches_drift: "
                  "checker returned 0 on poisoned template",
                  "expected non-zero")
            return
    _ok("test_8_alignment_checker_catches_drift")


# ---------------------------------------------------------------- main


def main() -> int:
    print("command_generator_smoke.py — ACT-7B")
    print()

    test_1_report_phase_single_line()
    test_2_report_review_rejects_unsupported_flags()
    test_3_export_public_data_multi_project_id()
    test_4_shlex_quote_for_values_with_spaces()
    test_5_unknown_subcommand_returns_nonzero()
    test_6_no_newline_no_continuation_in_output()
    test_7_alignment_checker_passes_on_real_templates()
    test_8_alignment_checker_catches_drift()

    print()
    if errors:
        print(f"command_generator_smoke.py: FAIL ({len(errors)} issue(s))")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("command_generator_smoke.py: PASS (8/8)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
