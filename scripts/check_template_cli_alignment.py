#!/usr/bin/env python3
"""
check_template_cli_alignment.py — ACT-7B template / CLI alignment check.

Problem it solves
-----------------
ACT-8 trial (commit f8543d3) found real, reproducible drift between
``templates/telegram/*.txt`` and the real CLI surface in
``scripts/tower.py``. Examples that actually appeared in the field:

  * ``report-handoff.txt`` listed ``--agent-id`` / ``--to-agent``
    instead of the real ``--from-agent-id`` / ``--to-agent-id``.
    An agent copying the template verbatim would have got a hard
    argparse error.
  * Older drafts of ``report-review.txt`` listed ``--source-repo``
    and ``--design-reason``. The current CLI does not accept those
    on report-review. argparse would have rejected the call.

This script catches the class of bug, not just the two known
instances, by reading the **same** SCHEMA dict that
``generate_tower_command.py`` uses (single source of truth), scanning
every template's "Command:" block, and cross-checking the
``--flag`` tokens it finds against the per-subcommand schema.

It also enforces a small set of static rules that have nothing to do
with the CLI surface (e.g. no ``git add .`` in the boilerplate).

How the check works (key design choices)
----------------------------------------
* The CLI surface check ONLY inspects the ``Command:`` block of a
  template (from the line ``Command:`` to the next blank line or
  end-of-file). Mentions of ``--source-repo`` in the "Hard rules"
  section that just *describe* another command do NOT count.
* The placeholder rule is advisory (WARN), not FAIL: most templates
  have a *literal* example command showing the user where to put
  their value. That is the whole point. The WARN is to make sure
  future authors are aware.

Exit codes
----------
  0  CLEAN (or FAIL: 0 / WARN-only)
  1  one or more FAILs (real drift; must fix)
  2  bad invocation or missing file
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from generate_tower_command import SCHEMA  # noqa: E402

REPO_ROOT = HERE.parent
TEMPLATES_DIR = REPO_ROOT / "templates" / "telegram"

# A template is "about" a subcommand if the subcommand name appears
# in the Command: block. A template that mentions report-review in
# prose but never as the leading token of the command does not get
# checked against report-review's schema.
SUBCOMMAND_KEYWORDS: dict[str, str] = {
    "register-agent":     "register-agent",
    "register-project":   "register-project",
    "report-phase":       "report-phase",
    "report-failure":     "report-failure",
    "report-review":      "report-review",
    "report-handoff":     "report-handoff",
    "report-release":     "report-release",
    "export-public-data": "export-public-data",
    "export_public_data": "export-public-data",
}

# A flag is a flag: --word, with the word starting with a letter
# and continuing with [a-z0-9-]. Catches --source-repo but not the
# typo'd "--target-" in a markdown emphasis ("--target-*").
FLAG_RE = re.compile(r"--[a-z][a-z0-9]+(?:-[a-z0-9]+)*")


def _command_blocks(text: str) -> list[tuple[str, str]]:
    """Return a list of (header_line, body) for every command block.

    Recognizes two styles of "command block" header:

    * ``Command:`` — the ACT-1..ACT-7 plain style.
    * ``(A) RECOMMENDED`` / ``(A) ...command from the generator...`` /
      ``(B) MANUAL`` — the ACT-7B labelled style, where the
      ``(A)`` block is the generator form and the ``(B)`` block is
      the manual single-line form. Both must be schema-clean.

    A block continues until the first blank line AFTER at least
    one non-blank content line. A blank line immediately after the
    header is part of the block, not its terminator.
    """
    blocks: list[tuple[str, str]] = []
    lines = text.splitlines()
    n = len(lines)
    i = 0
    while i < n:
        line = lines[i]
        is_command = bool(re.match(r"^\s*Command\s*:\s*$", line))
        # ACT-7B labelled sections. We treat the start of a labelled
        # section as a block only when it is followed, in the next
        # non-blank line, by a python/scripts/... invocation. The
        # adjacent prose must describe the block, not be the block.
        is_labelled = bool(re.match(
            r"^\s*\(A\)\s+(RECOMM|MANUAL|Single|Generator|generator)",
            line,
        )) or bool(re.match(r"^\s*\(B\)\s+(MANUAL|Generator|generator)",
                             line))
        if is_command or is_labelled:
            start = i + 1
            j = start
            seen_content = False
            while j < n:
                cur = lines[j]
                if cur.strip() == "":
                    if not seen_content:
                        j += 1
                        continue
                    break
                seen_content = True
                j += 1
            blocks.append((line.rstrip(), "\n".join(lines[start:j])))
            i = j
            continue
        i += 1
    return blocks


def _subcommand_in_block(body: str) -> str | None:
    """Return the canonical subcommand the body is running, or None."""
    m = re.search(
        r"\b(tower\.py|export_public_data\.py)\s+"
        r"([a-z][a-z0-9_-]*)",
        body,
    )
    if m:
        return SUBCOMMAND_KEYWORDS.get(m.group(2))
    return None


def _flag_in_subcommand(flag: str, sub: str) -> tuple[bool, str]:
    schema = SCHEMA.get(sub, {})
    if flag in schema:
        return True, ""
    allowed = ", ".join(sorted(schema.keys()))
    return False, (
        f"Command: block uses {flag} for '{sub}', but tower.py does "
        f"not accept that flag. allowed: {allowed}"
    )


def _static_rules(path: Path, text: str) -> list[str]:
    issues: list[str] = []
    fname = path.name
    if re.search(r"(?m)^\s*git\s+add\s+\.\s*$", text):
        issues.append(
            f"{fname}: 'git add .' is forbidden; list files explicitly"
        )
    return issues


def _check_template(path: Path) -> tuple[list[str], list[str]]:
    """Return (fails, warns)."""
    fails: list[str] = []
    warns: list[str] = []
    text = path.read_text(encoding="utf-8")

    for header, body in _command_blocks(text):
        sub = _subcommand_in_block(body)
        if sub is None:
            continue
        flags = set(FLAG_RE.findall(body))
        for flag in flags:
            ok, msg = _flag_in_subcommand(flag, sub)
            if not ok:
                fails.append(f"{path.name}: {msg}")
        if re.search(r"<[A-Z_]+>", body):
            warns.append(
                f"{path.name}: Command: block has '<PLACEHOLDER>' "
                f"tokens. Templates are intentionally literal; that "
                f"is the design. ACT-7B generators should NOT replace "
                f"these — they exist for human copy-paste. WARN only."
            )

    fails.extend(_static_rules(path, text))
    return fails, warns


def main() -> int:
    if not TEMPLATES_DIR.is_dir():
        print(f"[FAIL] templates dir not found: {TEMPLATES_DIR}",
              file=sys.stderr)
        return 2

    files = sorted(TEMPLATES_DIR.glob("*.txt"))
    if not files:
        print(f"[WARN] no *.txt templates under {TEMPLATES_DIR}",
              file=sys.stderr)
        return 0

    all_fails: list[str] = []
    all_warns: list[str] = []
    for f in files:
        fails, warns = _check_template(f)
        all_fails.extend(fails)
        all_warns.extend(warns)

    print(f"check_template_cli_alignment: scanned {len(files)} template(s)")
    for f in files:
        print(f"  - {f.name}")

    if all_warns:
        print(f"\n  {len(all_warns)} WARN(s) (advisory, do not block):")
        for w in all_warns:
            print(f"    - {w}")

    if all_fails:
        print(f"\n[FAIL] {len(all_fails)} real drift issue(s):")
        for f in all_fails:
            print(f"  - {f}")
        return 1

    print("\ncheck_template_cli_alignment: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
