#!/usr/bin/env python3
"""
generate_tower_command.py — ACT-7B tower command generator.

Why this exists
---------------
ACT-8 multi-agent onboarding trial (commit f8543d3) found that trial
agents hand-writing long multi-line bash commands (line-continuation
backslashes, multi-line string args) repeatedly broke the call to
``scripts/tower.py``:

  - bash line-continuation (``\\``) collapses multi-line into one
    argument, sometimes joined into a single token the CLI rejects.
  - string args with embedded spaces or apostrophes (e.g. "ACT-7
    Playbook Review by Second Agent") were not quoted, causing
    argparse to slice them.
  - some templates still listed flags the tower.py subcommand does
    not actually accept (e.g. ``--source-repo`` on ``report-review``),
    which argparse rejects with a hard error.

This script is a *single-source-of-truth* command generator:

  1. Each tower.py subcommand has a hard-coded schema of allowed
     flags (matches ``scripts/tower.py build_parser()`` byte-for-byte).
  2. Any flag you pass that is NOT in the schema → hard FAIL. The
     generator refuses to print a broken command.
  3. Any string value with whitespace, quote characters, or shell
     metacharacters is wrapped via ``shlex.quote`` so it survives
     one round of bash parsing.
  4. The output is a *single line*. No ``\\`` continuations. No
     multi-line strings. Paste it into a shell, the command runs.
  5. The generator NEVER executes the command. It only prints it to
     stdout. There is no ``--execute`` flag, by design.

Design rules
------------
  * stdlib only.
  * Never touches data/, public-data/, or generated/.
  * Never runs git, never pushes, never exports.
  * The schema in this file is the SAME data the template
    consistency check uses; they cannot drift by construction.

Usage
-----
  python scripts/generate_tower_command.py <subcommand> \\
      --project-id booktrans-desk \\
      --agent-id local-hermes \\
      ...

  python scripts/generate_tower_command.py <subcommand> --explain
    # print the schema for that subcommand, no command output.

  python scripts/generate_tower_command.py --list
    # list all supported subcommands.

Exit codes
----------
  0  command (or schema / list) printed
  2  unknown subcommand or unknown flag
  3  missing required flag
  4  invalid value (out of choices)
"""
from __future__ import annotations

import argparse
import shlex
import sys
from typing import Any, Callable


# ---------------------------------------------------------------- schema
#
# Each entry is: { flag_name: (attr, kind, required, choices_or_None) }
#
#   kind in {"str", "int", "append"}:
#     - "str"    : one string value
#     - "int"    : integer
#     - "append" : --flag may appear multiple times, collected into a list
#
# choices_or_None is a tuple of allowed string values, or None for free-form.
#
# This is the single source of truth that BOTH the generator and
# scripts/check_template_cli_alignment.py read. Keep it in sync with
# scripts/tower.py build_parser(). If you add a flag to tower.py, add
# it here, or both tools will reject the new flag.
# ----------------------------------------------------------------

SCHEMA: dict[str, dict[str, tuple[str, str, bool, tuple[str, ...] | None]]] = {

    "register-agent": {
        "--agent-id":     ("agent_id", "str", True,  None),
        "--name":         ("name",     "str", False, None),
        "--display-name": ("display_name", "str", False, None),
        "--machine":      ("machine",  "str", False, None),
        "--role":         ("role",     "str", False, None),
        "--operator":     ("operator", "str", False, None),
    },

    "register-project": {
        "--project-id":  ("project_id", "str", True,  None),
        "--name":        ("name",       "str", False, None),
        "--repo":        ("repo",       "str", True,  None),
        "--location":    ("location",   "str", False, ("local", "public")),
        "--category":    ("category",   "str", False, None),
        "--status":      ("status",     "str", False, None),
        "--description": ("description","str", False, None),
        "--agent-id":    ("agent_id",   "str", False, None),
    },

    "report-phase": {
        "--project-id":        ("project_id", "str", True,  None),
        "--agent-id":          ("agent_id",   "str", True,  None),
        "--phase-id":          ("phase_id",   "str", True,  None),
        "--phase-name":        ("phase_name", "str", False, None),
        "--status":            ("status",     "str", True,
                                ("PASS", "FAIL", "PARTIAL", "BLOCKED", "PAUSED", "SKIPPED")),
        "--health":            ("health",     "str", False, None),
        "--summary":           ("summary",    "str", True,  None),
        "--next":              ("next_list",  "append", False, None),
        "--source-repo":       ("source_repo","str", False, None),
        "--source-commit":     ("source_commit","str", False, None),
        "--source-commit-url": ("source_commit_url","str", False, None),
    },

    "report-failure": {
        "--project-id":        ("project_id", "str", True,  None),
        "--agent-id":          ("agent_id",   "str", True,  None),
        "--phase-id":          ("phase_id",   "str", True,  None),
        "--phase-name":        ("phase_name", "str", False, None),
        "--summary":           ("summary",    "str", True,  None),
        "--failure-reason":    ("failure_reason","str", True, None),
        "--next":              ("next",       "str", False, None),
        "--source-repo":       ("source_repo","str", False, None),
        "--source-commit":     ("source_commit","str", False, None),
        "--source-commit-url": ("source_commit_url","str", False, None),
    },

    # NOTE: report-review does NOT accept --source-repo / --source-commit.
    # It uses --target-* instead. This is a real tower.py invariant, not
    # an oversight, and the alignment checker will FAIL any template
    # that still lists --source-* on a report-review command.
    "report-review": {
        "--project-id":     ("project_id",     "str", True,  None),
        "--agent-id":       ("agent_id",       "str", True,  None),
        "--phase-id":       ("phase_id",       "str", True,  None),
        "--phase-name":     ("phase_name",     "str", False, None),
        "--status":         ("status",         "str", True,
                            ("PASS", "FAIL", "COMMENT_ONLY")),
        "--health":         ("health",         "str", False, None),
        "--summary":        ("summary",        "str", True,  None),
        "--next":           ("next",           "str", False, None),
        "--target-agent-id":("target_agent_id","str", True,  None),
        "--target-phase-id":("target_phase_id","str", True,  None),
        "--target-commit":  ("target_commit",  "str", False, None),
    },

    "report-handoff": {
        "--project-id":     ("project_id",     "str", True,  None),
        "--from-agent-id":  ("from_agent_id",  "str", True,  None),
        "--to-agent-id":    ("to_agent_id",    "str", True,  None),
        "--current-phase":  ("current_phase",  "str", True,  None),
        "--reason":         ("reason",         "str", True,  None),
    },

    "report-release": {
        "--project-id":     ("project_id",     "str", True,  None),
        "--agent-id":       ("agent_id",       "str", True,  None),
        "--version":        ("version",        "str", True,  None),
        "--summary":        ("summary",        "str", True,  None),
        "--source-repo":    ("source_repo",    "str", False, None),
        "--source-commit":  ("source_commit",  "str", False, None),
        "--release-url":    ("release_url",    "str", False, None),
    },

    # export-public-data is a different binary (scripts/export_public_data.py)
    # but lives under the same "tower-ish" command family. Same generator,
    # same rules. The flags here match export_public_data.py build_parser.
    "export-public-data": {
        "--source":      ("source",      "str", True,
                           ("data", "examples", "public-data")),
        "--output":      ("output",      "str", True,  None),
        "--project-id":  ("project_ids", "append", False, None),
        "--agent-id":    ("agent_ids",   "append", False, None),
        "--max-events":  ("max_events",  "int",  False, None),
        "--repo-prefix": ("repo_prefix", "str",  False, None),
        "--replace":     ("replace",     "bool", False, None),
    },
}


# ---------------------------------------------------------------- helpers


def _needs_quote(value: str) -> bool:
    """A value needs shlex.quote if it contains any character that bash
    would interpret or split on."""
    if not value:
        return True
    safe = set(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789"
        "_-./:="
    )
    return any(c not in safe for c in value)


def _render_value(value: str) -> str:
    """Render a value as a single shell token. Always safe to paste."""
    if _needs_quote(value):
        return shlex.quote(value)
    return value


def _validate_choice(flag: str, value: str,
                     choices: tuple[str, ...] | None) -> str | None:
    if choices is None:
        return None
    if value not in choices:
        return (
            f"  [FAIL] {flag}={value!r} is not a valid choice.\n"
            f"         allowed: {', '.join(choices)}"
        )
    return None


def _check_unknown_flags(subcommand: str, raw_argv: list[str]) -> list[str]:
    """Any --flag not in SCHEMA[subcommand] is a hard error."""
    schema = SCHEMA[subcommand]
    errors: list[str] = []
    for token in raw_argv:
        if not token.startswith("--"):
            continue
        flag = token.split("=", 1)[0]
        if flag not in schema:
            allowed = ", ".join(sorted(schema.keys()))
            errors.append(
                f"  [FAIL] {flag} is NOT a valid flag for "
                f"'{subcommand}'.\n"
                f"         allowed flags: {allowed}"
            )
    return errors


def _check_required(subcommand: str,
                    present: set[str]) -> list[str]:
    schema = SCHEMA[subcommand]
    errors: list[str] = []
    for flag, (attr, kind, required, choices) in schema.items():
        if required and flag not in present:
            errors.append(f"  [FAIL] missing required flag: {flag}")
    return errors


def _format_command(subcommand: str, parsed: dict[str, Any]) -> str:
    """Render a single-line bash command. No newlines, no continuations."""
    parts: list[str] = ["python", "scripts/tower.py", subcommand]
    schema = SCHEMA[subcommand]

    # Emit in schema order so output is deterministic and diff-friendly.
    for flag, (attr, kind, required, choices) in schema.items():
        if attr not in parsed:
            continue
        v = parsed[attr]
        if kind == "append":
            assert isinstance(v, list)
            for item in v:
                parts.extend([flag, _render_value(str(item))])
        elif kind == "bool":
            if v:
                parts.append(flag)
        else:
            parts.extend([flag, _render_value(str(v))])
    return " ".join(parts)


# ---------------------------------------------------------------- CLI


def _print_explain(subcommand: str) -> int:
    if subcommand not in SCHEMA:
        print(f"[FAIL] unknown subcommand: {subcommand}", file=sys.stderr)
        print(f"       supported: {', '.join(SCHEMA.keys())}", file=sys.stderr)
        return 2
    print(f"schema for: {subcommand}")
    print()
    for flag, (attr, kind, required, choices) in sorted(SCHEMA[subcommand].items()):
        marker = "REQUIRED" if required else "optional"
        type_str = kind
        ch = f"  choices={list(choices)}" if choices else ""
        print(f"  {flag:24s}  {marker:9s}  {type_str}{ch}")
    print()
    print("render rules:")
    print("  - all values are single shell tokens (shlex.quote when needed)")
    print("  - output is a single line, no '\\\\' continuations")
    print("  - this generator NEVER executes the command")
    return 0


def _print_list() -> int:
    print("supported subcommands:")
    for sub in SCHEMA:
        print(f"  {sub}")
    print()
    print("use --explain <sub> for the flag schema.")
    print("this script only PRINTS commands; it does not run them.")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]

    # meta-flags first
    if "--list" in argv:
        return _print_list()

    if not argv or argv[0] in ("-h", "--help"):
        first_line = (__doc__ or "").splitlines()[0] if __doc__ else "tower command generator"
        print(first_line)
        print()
        print("usage:")
        print("  python scripts/generate_tower_command.py <subcommand> [flags...]")
        print("  python scripts/generate_tower_command.py <subcommand> --explain")
        print("  python scripts/generate_tower_command.py --list")
        print()
        print("supported subcommands:")
        for sub in SCHEMA:
            print(f"  {sub}")
        return 0

    subcommand = argv[0]
    rest = argv[1:]

    if subcommand not in SCHEMA:
        print(f"[FAIL] unknown subcommand: {subcommand}", file=sys.stderr)
        print(f"       supported: {', '.join(SCHEMA.keys())}", file=sys.stderr)
        return 2

    if "--explain" in rest:
        return _print_explain(subcommand)

    # unknown-flag check on the raw argv (catches typos before argparse)
    unknown_errors = _check_unknown_flags(subcommand, rest)
    if unknown_errors:
        print(f"[FAIL] invalid flag(s) for '{subcommand}':", file=sys.stderr)
        for e in unknown_errors:
            print(e, file=sys.stderr)
        return 2

    # parse the rest with a tiny pass-through parser
    schema = SCHEMA[subcommand]
    parsed: dict[str, Any] = {}
    present: set[str] = set()
    i = 0
    while i < len(rest):
        token = rest[i]
        if not token.startswith("--"):
            print(f"[FAIL] unexpected positional token: {token!r}",
                  file=sys.stderr)
            return 2

        if "=" in token:
            flag, _, value = token.partition("=")
        else:
            flag = token
            attr, kind, required, choices = schema[flag]
            # bool flags are standalone: --replace with no value
            if kind == "bool":
                parsed[attr] = True
                present.add(flag)
                i += 1
                continue
            if i + 1 >= len(rest):
                print(f"[FAIL] {flag} needs a value", file=sys.stderr)
                return 2
            value = rest[i + 1]
            i += 1
        i += 1

        attr, kind, required, choices = schema[flag]
        present.add(flag)

        if kind == "bool":
            parsed[attr] = True
            continue

        if kind == "int":
            try:
                intval = int(value)
            except ValueError:
                print(f"[FAIL] {flag}={value!r} is not an integer",
                      file=sys.stderr)
                return 4
            parsed[attr] = intval
            continue

        # str / append share the same path; append collects into a list
        err = _validate_choice(flag, value, choices)
        if err is not None:
            print(err, file=sys.stderr)
            return 4

        if kind == "append":
            parsed.setdefault(attr, []).append(value)
        else:
            parsed[attr] = value

    # required check
    missing = _check_required(subcommand, present)
    if missing:
        print(f"[FAIL] '{subcommand}' is missing required flag(s):",
              file=sys.stderr)
        for m in missing:
            print(m, file=sys.stderr)
        return 3

    # final: render and print. NEVER execute.
    cmd = _format_command(subcommand, parsed)
    print(cmd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
