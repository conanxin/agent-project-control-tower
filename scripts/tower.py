"""
tower.py — the unified control tower CLI.

Subcommands (all stdlib, no third-party deps):

  python scripts/tower.py validate                 [default: --source data]
  python scripts/tower.py build                    [default: --source data]
  python scripts/tower.py register-agent ...
  python scripts/tower.py register-project ...
  python scripts/tower.py report-phase ...
  python scripts/tower.py report-failure ...
  python scripts/tower.py report-review ...
  python scripts/tower.py report-handoff ...
  python scripts/tower.py report-release ...
  python scripts/tower.py seed                     # copy examples/ → data/

Conventions
-----------
- Every write goes under data/registry/ or data/events/.
- Filenames for events are timestamped so they sort chronologically:
      data/events/YYYYMMDDTHHMMSSZ_<event_type>_<agent_id>__<project_id>[__<phase>].json
- We never auto-commit / auto-push. The agent (or a human) reviews and
  commits separately. This is intentional: see docs/AGENT_WORKFLOW.md.
- Re-running any register-*/report-* is idempotent on registry entries
  (it won't duplicate) but ALWAYS writes a new event (append-only).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lib"))

from yaml_mini import load as load_yaml, loads as yaml_loads  # noqa: E402
from redaction import check_payload  # noqa: E402

# Allow tests / multi-checkout setups to override the repo root via env var.
# Production callers just run from the repo root and ignore this.
ROOT = Path(os.environ.get("TOWER_ROOT", HERE.parent)).resolve()
DATA = ROOT / "data"
REGISTRY = DATA / "registry"
EVENTS = DATA / "events"
EXAMPLES = ROOT / "examples"

# Fields checked for privacy on writes. Most event payloads funnel through
# these keys; unknown keys still get checked if they're strings.
PRIVACY_FIELDS: tuple[str, ...] = (
    "summary", "description", "reason", "failure_reason", "next",
    "design_reason", "impact_analysis",
    "repo", "source_repo", "release_url", "source_commit_url",
    "name", "display_name",
)


# --------------------------------------------------------------------- utils


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ts_compact(dt: datetime | None = None) -> str:
    return (dt or _now()).strftime("%Y%m%dT%H%M%SZ")


def _ts_human(dt: datetime | None = None) -> str:
    return (dt or _now()).strftime("%Y-%m-%dT%H:%M:%SZ")


def _gen_event_id() -> str:
    return str(uuid.uuid4())


def _read_yaml(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = load_yaml(str(path))
    return data if isinstance(data, list) else []


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _write_yaml_append(path: Path, new_record: dict[str, Any], id_field: str) -> tuple[bool, str]:
    """Append a record to a YAML list file. Returns (added, reason)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = _read_text(path).rstrip()
    # Check duplicates by id
    if raw:
        existing = _read_yaml(path)
        for r in existing:
            if r.get(id_field) == new_record.get(id_field):
                return False, f"already exists (id={new_record.get(id_field)!r})"

    new_id = new_record.get(id_field) or "?"
    block_lines: list[str] = []
    if not raw or not raw.endswith("\n---\n") and not raw.endswith("\n"):
        if raw:
            raw = raw + "\n"
    block_lines.append(f"# registered { _ts_human() } via tower.py\n")
    # First key gets the `- ` dash; subsequent keys are indented under it.
    items = list(new_record.items())
    if items:
        first_key, first_value = items[0]
        block_lines.append(f"- {first_key}: {_yaml_scalar(first_value)}\n")
        for key, value in items[1:]:
            block_lines.append(f"  {key}: {_yaml_scalar(value)}\n")
    if raw:
        raw = raw + "\n"
    raw = raw + "".join(block_lines)
    path.write_text(raw, encoding="utf-8")
    return True, f"registered id={new_id!r}"


def _yaml_scalar(value: Any) -> str:
    """Format a Python value as a YAML scalar (or inline list)."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        # Inline list. yaml_mini supports `[a, b, c]` syntax.
        return "[" + ", ".join(json.dumps(v, ensure_ascii=False) for v in value) + "]"
    if isinstance(value, str):
        # Use single-quoted YAML to be safe; double single quotes inside.
        escaped = value.replace("'", "''")
        return f"'{escaped}'"
    return json.dumps(value, ensure_ascii=False)


def _privacy_ok(payload: dict[str, Any], strict: bool = True) -> tuple[bool, list[str]]:
    """Run redaction check on a payload. Returns (ok, [reasons]).

    `ok=False` only when there is at least one FAIL severity finding. WARN
    findings are returned but allowed by default.
    """
    fields_to_scan = {k: v for k, v in payload.items() if k in PRIVACY_FIELDS and isinstance(v, str)}
    if not fields_to_scan:
        return True, []
    severity, reasons = check_payload(fields_to_scan)
    if severity == "FAIL":
        return False, reasons
    return True, reasons


def _write_event(
    event: dict[str, Any],
    *,
    event_type_short: str,
    agent_id: str,
    project_id: str,
    phase_id: str | None = None,
) -> Path:
    """Write an event to data/events/ with a deterministic filename.

    Filename: YYYYMMDDTHHMMSSZ_<short>_<agent>__<project>[__<phase>].json
    """
    ts = _ts_compact()
    safe = lambda s: "".join(c for c in (s or "") if c.isalnum() or c in "-_")
    parts = [ts, event_type_short, safe(agent_id), safe(project_id)]
    if phase_id:
        parts.append(safe(phase_id))
    fname = "__".join(parts) + ".json"
    path = EVENTS / fname
    EVENTS.mkdir(parents=True, exist_ok=True)
    if path.exists():
        # append a counter to keep filenames unique within a second
        i = 1
        while True:
            alt = path.with_name(f"{path.stem}_{i}.json")
            if not alt.exists():
                path = alt
                break
            i += 1
    path.write_text(json.dumps(event, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _validate_and_build() -> int:
    """Run validate + build at the end of any mutating command.

    Validate and build are run independently. A validate failure does NOT
    stop build — the user always gets a fresh generated/index.json so they
    can see what their write did. The validate output goes to stderr-style
    messaging; build keeps stdout.
    """
    print()
    print("--- post-write: validate + build ---")
    # Pass --root so subprocesses operate on the same data/ as tower.py.
    extra = ["--root", str(ROOT)]
    r1 = subprocess.run(
        [sys.executable, str(HERE / "validate.py"), "--source", "data", *extra],
        capture_output=False,
    )
    r2 = subprocess.run(
        [sys.executable, str(HERE / "build_index.py"), "--source", "data", *extra],
        capture_output=False,
    )
    if r2.returncode != 0:
        return r2.returncode
    return r1.returncode


# ----------------------------------------------------------------- subcommands


def cmd_validate(args: argparse.Namespace) -> int:
    return subprocess.call(
        [sys.executable, str(HERE / "validate.py"), "--source", args.source]
    )


def cmd_build(args: argparse.Namespace) -> int:
    extra = ["--root", str(ROOT)]
    r = subprocess.call(
        [
            sys.executable, str(HERE / "build_index.py"),
            "--source", args.source, *extra,
        ]
    )
    if r != 0:
        return r
    if not args.no_embedded:
        # The embedded builder reads from generated/index.json (relative to
        # the cwd or absolute path). Build wrote it under ROOT/generated,
        # so point --index at that absolute path.
        idx = ROOT / "generated" / "index.json"
        tpl = ROOT / "site" / "index.html"
        out_html = ROOT / "site" / "index.embedded.html"
        subprocess.run(
            [
                sys.executable, str(HERE / "build_embedded_site.py"),
                "--index", str(idx),
                "--template", str(tpl),
                "--output", str(out_html),
            ],
            check=False,
        )
    return 0


def cmd_seed(args: argparse.Namespace) -> int:
    """Copy examples/registry and examples/events to data/, if data/ is empty."""
    if not EXAMPLES.exists():
        print(f"  [FAIL] examples dir not found: {EXAMPLES}")
        return 1
    REGISTRY.mkdir(parents=True, exist_ok=True)
    EVENTS.mkdir(parents=True, exist_ok=True)

    # registry
    src_reg = EXAMPLES / "registry"
    if src_reg.exists():
        for f in src_reg.iterdir():
            dst = REGISTRY / f.name
            if dst.exists() and not args.force:
                print(f"  [skip] {dst.relative_to(ROOT)} already exists")
            else:
                dst.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
                print(f"  [ok] seeded {dst.relative_to(ROOT)}")
    # events
    src_evt = EXAMPLES / "events"
    if src_evt.exists():
        for f in src_evt.iterdir():
            dst = EVENTS / f.name
            if dst.exists() and not args.force:
                print(f"  [skip] {dst.relative_to(ROOT)} already exists")
            else:
                dst.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
                print(f"  [ok] seeded {dst.relative_to(ROOT)}")
    return 0


def _common_register_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    """Pull common privacy-checked fields out of a Namespace."""
    return {k: v for k, v in vars(args).items() if isinstance(v, str) and k in PRIVACY_FIELDS}


def cmd_register_agent(args: argparse.Namespace) -> int:
    if not args.agent_id:
        print("  [FAIL] --agent-id is required")
        return 2
    record: dict[str, Any] = {
        "id": args.agent_id,
        "name": args.name or args.agent_id,
        "machine": args.machine or "local",
        "role": args.role or "agent",
        "status": "ACTIVE",
    }
    if args.display_name:
        record["display_name"] = args.display_name
    if args.operator:
        record["operator"] = args.operator

    # Privacy on string fields
    ok, reasons = _privacy_ok(record)
    if not ok:
        print(f"  [FAIL] privacy check failed:\n    " + "\n    ".join(reasons))
        return 3
    if reasons:
        print("  [WARN] privacy warnings:\n    " + "\n    ".join(reasons))

    added, msg = _write_yaml_append(REGISTRY / "agents.yml", record, "id")
    print(f"  agents.yml: {msg}")

    if added:
        event: dict[str, Any] = {
            "event_type": "AGENT_REGISTERED",
            "event_id": _gen_event_id(),
            "created_at": _ts_human(),
            # AGENT_REGISTERED is not a project event; project_id intentionally
            # omitted (validate treats it as optional for this type).
            "agent_id": args.agent_id,
            "status": "ACTIVE",
            "health": "green",
            "summary": f"agent {args.agent_id!r} registered: {record.get('name')}",
            "next": None,
        }
        path = _write_event(
            event,
            event_type_short="AGENT_REG",
            agent_id=args.agent_id,
            project_id=args.agent_id,
        )
        print(f"  event: {path.relative_to(ROOT)}")

    return _validate_and_build()


def cmd_register_project(args: argparse.Namespace) -> int:
    if not args.project_id:
        print("  [FAIL] --project-id is required")
        return 2
    record: dict[str, Any] = {
        "id": args.project_id,
        "name": args.name or args.project_id,
        "repo": args.repo,
        "location": args.location or "local",
        "category": args.category or "uncategorized",
        "status": args.status or "ACTIVE",
        "description": args.description or "",
        "primary_agent": args.agent_id or "",
    }
    ok, reasons = _privacy_ok(record)
    if not ok:
        print(f"  [FAIL] privacy check failed:\n    " + "\n    ".join(reasons))
        return 3
    if reasons:
        print("  [WARN] privacy warnings:\n    " + "\n    ".join(reasons))

    added, msg = _write_yaml_append(REGISTRY / "projects.yml", record, "id")
    print(f"  projects.yml: {msg}")

    if added:
        event: dict[str, Any] = {
            "event_type": "PROJECT_REGISTERED",
            "event_id": _gen_event_id(),
            "created_at": _ts_human(),
            "project_id": args.project_id,
            "agent_id": args.agent_id or args.project_id,
            "status": "ACTIVE",
            "health": "green",
            "summary": f"project {args.project_id!r} registered: {record.get('name')}",
            "next": None,
        }
        if args.repo:
            event["source_repo"] = args.repo
        if args.description:
            event["description"] = args.description
        path = _write_event(
            event,
            event_type_short="PROJECT_REG",
            agent_id=event["agent_id"],
            project_id=args.project_id,
        )
        print(f"  event: {path.relative_to(ROOT)}")

    return _validate_and_build()


def _build_phase_event(args: argparse.Namespace, status: str, health: str) -> dict[str, Any]:
    next_val = None
    if getattr(args, "next_list", None):
        next_val = args.next_list[0]
    elif getattr(args, "next", None):
        next_val = args.next

    return {
        "event_type": "PHASE_REPORT",
        "event_id": _gen_event_id(),
        "created_at": _ts_human(),
        "project_id": args.project_id,
        "agent_id": args.agent_id,
        "status": status,
        "health": health,
        "summary": args.summary,
        "phase_id": args.phase_id,
        "phase_name": args.phase_name or args.phase_id,
        "next": next_val,
        "source_repo": args.source_repo,
        "source_commit": args.source_commit,
        "source_commit_url": args.source_commit_url,
    }


def cmd_report_phase(args: argparse.Namespace) -> int:
    for k in ("project_id", "agent_id", "phase_id", "status", "summary"):
        if not getattr(args, k):
            print(f"  [FAIL] --{k.replace('_', '-')} is required")
            return 2
    status = args.status
    health = args.health or {
        "PASS": "green", "FAIL": "red", "PARTIAL": "yellow",
        "BLOCKED": "red", "PAUSED": "gray", "SKIPPED": "gray",
    }.get(status, "gray")

    event = _build_phase_event(args, status, health)
    if args.next_list:
        # Allow multiple --next values; first one is the canonical, rest are
        # appended as a list under "next_extra" for richer dashboards.
        event["next"] = args.next_list[0]
        if len(args.next_list) > 1:
            event["next_extra"] = args.next_list[1:]
    elif getattr(args, "next", None):
        event["next"] = args.next

    ok, reasons = _privacy_ok(event)
    if not ok:
        print(f"  [FAIL] privacy check failed:\n    " + "\n    ".join(reasons))
        return 3
    if reasons:
        print("  [WARN] privacy warnings:\n    " + "\n    ".join(reasons))

    path = _write_event(
        event,
        event_type_short="PHASE",
        agent_id=args.agent_id,
        project_id=args.project_id,
        phase_id=args.phase_id,
    )
    print(f"  event: {path.relative_to(ROOT)}")
    return _validate_and_build()


def cmd_report_failure(args: argparse.Namespace) -> int:
    """Shortcut: a PHASE_REPORT with status=FAIL, health=red, and
    a required --failure-reason field."""
    for k in ("project_id", "agent_id", "phase_id", "summary", "failure_reason"):
        if not getattr(args, k):
            print(f"  [FAIL] --{k.replace('_', '-')} is required")
            return 2
    # Synthesize a phase event then patch in failure_reason.
    args.status = "FAIL"
    args.health = "red"
    event = _build_phase_event(args, "FAIL", "red")
    event["failure_reason"] = args.failure_reason
    if getattr(args, "next", None):
        event["next"] = args.next

    ok, reasons = _privacy_ok(event)
    if not ok:
        print(f"  [FAIL] privacy check failed:\n    " + "\n    ".join(reasons))
        return 3
    if reasons:
        print("  [WARN] privacy warnings:\n    " + "\n    ".join(reasons))

    path = _write_event(
        event,
        event_type_short="FAILURE",
        agent_id=args.agent_id,
        project_id=args.project_id,
        phase_id=args.phase_id,
    )
    print(f"  event: {path.relative_to(ROOT)}")
    return _validate_and_build()


def cmd_report_review(args: argparse.Namespace) -> int:
    for k in ("project_id", "agent_id", "phase_id", "status", "summary",
              "target_agent_id", "target_phase_id"):
        if not getattr(args, k):
            print(f"  [FAIL] --{k.replace('_', '-')} is required")
            return 2
    event: dict[str, Any] = {
        "event_type": "REVIEW_REPORT",
        "event_id": _gen_event_id(),
        "created_at": _ts_human(),
        "project_id": args.project_id,
        "agent_id": args.agent_id,
        "status": args.status,
        "health": args.health or {
            "PASS": "green", "FAIL": "red", "COMMENT_ONLY": "gray",
        }.get(args.status, "gray"),
        "summary": args.summary,
        "phase_id": args.phase_id,
        "phase_name": args.phase_name or args.phase_id,
        "next": args.next,
        "review_target": {
            "agent_id": args.target_agent_id,
            "phase_id": args.target_phase_id,
            "commit": args.target_commit,
        },
    }
    ok, reasons = _privacy_ok(event)
    if not ok:
        print(f"  [FAIL] privacy check failed:\n    " + "\n    ".join(reasons))
        return 3
    if reasons:
        print("  [WARN] privacy warnings:\n    " + "\n    ".join(reasons))

    path = _write_event(
        event,
        event_type_short="REVIEW",
        agent_id=args.agent_id,
        project_id=args.project_id,
        phase_id=args.phase_id,
    )
    print(f"  event: {path.relative_to(ROOT)}")
    return _validate_and_build()


def cmd_report_handoff(args: argparse.Namespace) -> int:
    for k in ("project_id", "from_agent_id", "to_agent_id", "current_phase", "reason"):
        if not getattr(args, k):
            print(f"  [FAIL] --{k.replace('_', '-')} is required")
            return 2
    event: dict[str, Any] = {
        "event_type": "HANDOFF",
        "event_id": _gen_event_id(),
        "created_at": _ts_human(),
        "project_id": args.project_id,
        "agent_id": args.from_agent_id,
        "status": "ACTIVE",
        "health": "gray",
        "summary": f"handoff {args.from_agent_id} → {args.to_agent_id} on {args.current_phase}",
        "handoff": {
            "from_agent_id": args.from_agent_id,
            "to_agent_id": args.to_agent_id,
            "current_phase": args.current_phase,
            "reason": args.reason,
        },
    }
    ok, reasons = _privacy_ok(event)
    if not ok:
        print(f"  [FAIL] privacy check failed:\n    " + "\n    ".join(reasons))
        return 3
    if reasons:
        print("  [WARN] privacy warnings:\n    " + "\n    ".join(reasons))

    path = _write_event(
        event,
        event_type_short="HANDOFF",
        agent_id=args.from_agent_id,
        project_id=args.project_id,
    )
    print(f"  event: {path.relative_to(ROOT)}")
    return _validate_and_build()


def cmd_report_release(args: argparse.Namespace) -> int:
    for k in ("project_id", "agent_id", "version", "summary"):
        if not getattr(args, k):
            print(f"  [FAIL] --{k.replace('_', '-')} is required")
            return 2
    event: dict[str, Any] = {
        "event_type": "RELEASE",
        "event_id": _gen_event_id(),
        "created_at": _ts_human(),
        "project_id": args.project_id,
        "agent_id": args.agent_id,
        "status": "RELEASED",
        "health": "green",
        "summary": args.summary,
        "release": {
            "version": args.version,
            "source_repo": args.source_repo,
            "source_commit": args.source_commit,
            "release_url": args.release_url,
        },
    }
    ok, reasons = _privacy_ok(event)
    if not ok:
        print(f"  [FAIL] privacy check failed:\n    " + "\n    ".join(reasons))
        return 3
    if reasons:
        print("  [WARN] privacy warnings:\n    " + "\n    ".join(reasons))

    path = _write_event(
        event,
        event_type_short="RELEASE",
        agent_id=args.agent_id,
        project_id=args.project_id,
    )
    print(f"  event: {path.relative_to(ROOT)}")
    return _validate_and_build()


# ----------------------------------------------------------------- argparse


def _add_common_source(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--source", choices=("data", "examples", "public-data"), default="data",
        help="dataset to operate on (default: data)"
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tower",
        description="Agent Project Control Tower — unified CLI (stdlib only)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # validate
    sp = sub.add_parser("validate", help="validate registry + events")
    _add_common_source(sp)
    sp.set_defaults(func=cmd_validate)

    # build
    sp = sub.add_parser("build", help="regenerate generated/index.json + embedded HTML")
    _add_common_source(sp)
    sp.add_argument("--no-embedded", action="store_true",
                    help="skip generating site/index.embedded.html")
    sp.set_defaults(func=cmd_build)

    # seed
    sp = sub.add_parser("seed", help="copy examples/ into data/ (initial setup)")
    sp.add_argument("--force", action="store_true",
                    help="overwrite existing files")
    sp.set_defaults(func=cmd_seed)

    # register-agent
    sp = sub.add_parser("register-agent", help="register an agent")
    sp.add_argument("--agent-id", required=True)
    sp.add_argument("--name", default=None)
    sp.add_argument("--display-name", default=None)
    sp.add_argument("--machine", default="local")
    sp.add_argument("--role", default="agent")
    sp.add_argument("--operator", default=None)
    sp.set_defaults(func=cmd_register_agent)

    # register-project
    sp = sub.add_parser("register-project", help="register a project")
    sp.add_argument("--project-id", required=True)
    sp.add_argument("--name", default=None)
    sp.add_argument("--repo", required=True)
    sp.add_argument("--location", default="local")
    sp.add_argument("--category", default="uncategorized")
    sp.add_argument("--status", default="ACTIVE")
    sp.add_argument("--description", default=None)
    sp.add_argument("--agent-id", default=None,
                    help="primary agent (becomes primary_agent in registry)")
    sp.set_defaults(func=cmd_register_project)

    # report-phase
    sp = sub.add_parser("report-phase", help="append a PHASE_REPORT event")
    sp.add_argument("--project-id", required=True)
    sp.add_argument("--agent-id", required=True)
    sp.add_argument("--phase-id", required=True)
    sp.add_argument("--phase-name", default=None)
    sp.add_argument("--status", required=True,
                    choices=("PASS", "FAIL", "PARTIAL", "BLOCKED", "PAUSED", "SKIPPED"))
    sp.add_argument("--health", default=None,
                    help="explicit health (default: derived from status)")
    sp.add_argument("--summary", required=True)
    sp.add_argument("--next", action="append", dest="next_list", default=None,
                    help="next-step; pass multiple times to add several")
    sp.add_argument("--source-repo", default=None)
    sp.add_argument("--source-commit", default=None)
    sp.add_argument("--source-commit-url", default=None)
    sp.set_defaults(func=cmd_report_phase)

    # report-failure
    sp = sub.add_parser("report-failure",
                        help="append a PHASE_REPORT (status=FAIL, health=red) with failure_reason")
    sp.add_argument("--project-id", required=True)
    sp.add_argument("--agent-id", required=True)
    sp.add_argument("--phase-id", required=True)
    sp.add_argument("--phase-name", default=None)
    sp.add_argument("--summary", required=True)
    sp.add_argument("--failure-reason", required=True)
    sp.add_argument("--next", default=None)
    sp.add_argument("--source-repo", default=None)
    sp.add_argument("--source-commit", default=None)
    sp.add_argument("--source-commit-url", default=None)
    sp.set_defaults(func=cmd_report_failure)

    # report-review
    sp = sub.add_parser("report-review", help="append a REVIEW_REPORT event")
    sp.add_argument("--project-id", required=True)
    sp.add_argument("--agent-id", required=True, help="the reviewer")
    sp.add_argument("--phase-id", required=True, help="the reviewer's own phase id")
    sp.add_argument("--phase-name", default=None)
    sp.add_argument("--status", required=True, choices=("PASS", "FAIL", "COMMENT_ONLY"))
    sp.add_argument("--health", default=None)
    sp.add_argument("--summary", required=True)
    sp.add_argument("--next", default=None)
    sp.add_argument("--target-agent-id", required=True)
    sp.add_argument("--target-phase-id", required=True)
    sp.add_argument("--target-commit", default=None)
    sp.set_defaults(func=cmd_report_review)

    # report-handoff
    sp = sub.add_parser("report-handoff", help="append a HANDOFF event")
    sp.add_argument("--project-id", required=True)
    sp.add_argument("--from-agent-id", required=True)
    sp.add_argument("--to-agent-id", required=True)
    sp.add_argument("--current-phase", required=True)
    sp.add_argument("--reason", required=True)
    sp.set_defaults(func=cmd_report_handoff)

    # report-release
    sp = sub.add_parser("report-release", help="append a RELEASE event")
    sp.add_argument("--project-id", required=True)
    sp.add_argument("--agent-id", required=True)
    sp.add_argument("--version", required=True)
    sp.add_argument("--summary", required=True)
    sp.add_argument("--source-repo", default=None)
    sp.add_argument("--source-commit", default=None)
    sp.add_argument("--release-url", default=None)
    sp.set_defaults(func=cmd_report_release)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
