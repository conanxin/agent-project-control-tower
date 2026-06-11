"""
validate.py — pre-flight check for the control tower registry + events.

Reads:
  <source>/registry/projects.yml
  <source>/registry/agents.yml
  <source>/events/*.json

Validates:
  1. projects registry parses as a list of project dicts.
  2. agents registry parses as a list of agent dicts.
  3. Every event JSON has the required fields and uses allowed enum values.
  4. Every event's project_id exists in projects registry.
  5. Every event's agent_id exists in agents registry.

Exits 0 on PASS, 1 on FAIL. Prints a human-readable summary.

--source {data,examples,both}  default: data
  data     – the live registry (default after ACT-2)
  examples – the curated examples seed
  both     – run both validators sequentially, fail if either fails
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lib"))

from yaml_mini import load as load_yaml  # noqa: E402

# -------------------------------------------------------------------- config

ALLOWED_STATUSES: set[str] = {
    "ACTIVE",
    "PASS",
    "FAIL",
    "PARTIAL",
    "BLOCKED",
    "PAUSED",
    "RELEASED",
    "ARCHIVED",
}

ALLOWED_EVENT_TYPES: set[str] = {
    "AGENT_REGISTERED",
    "PROJECT_REGISTERED",
    "PHASE_REPORT",
    "REVIEW_REPORT",
    "HANDOFF",
    "RELEASE",
    "FAILURE",
    "BLOCK",
    "UNBLOCK",
    "ARCHIVE",
}

# Required event fields common to all event types.
# (event_time OR created_at) is required for timestamp; handled in body.
REQUIRED_COMMON_FIELDS: tuple[str, ...] = (
    "event_type",
    "project_id",
    "agent_id",
    "status",
    "summary",
)

# Type-specific required fields.
TYPE_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "PHASE_REPORT":   ("phase_id", "health"),
    "REVIEW_REPORT":  ("phase_id", "review_target"),
    "HANDOFF":        ("handoff",),
    "RELEASE":        ("release",),
    "FAILURE":        ("failure_reason",),
}

TIMESTAMP_FIELDS: tuple[str, ...] = ("event_time", "created_at")

# ----------------------------------------------------------------- helpers


def _load_yaml_list(path: Path, kind: str, failures: list[str]) -> list[dict[str, Any]]:
    if not path.exists():
        failures.append(f"{kind} registry not found: {path}")
        return []
    try:
        data = load_yaml(str(path))
    except Exception as e:  # noqa: BLE001
        failures.append(f"{kind} registry parse error: {e}")
        return []
    if not isinstance(data, list):
        failures.append(f"{kind} registry must be a YAML list, got {type(data).__name__}")
        return []
    return data


def _load_event(path: Path, failures: list[str]) -> dict[str, Any] | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        failures.append(f"{path.name}: invalid JSON ({e})")
        return None
    except OSError as e:
        failures.append(f"{path.name}: cannot read ({e})")
        return None


def _validate_source(source_root: Path) -> tuple[bool, list[str], list[str]]:
    """Returns (ok, failures, warnings)."""
    failures: list[str] = []
    warnings: list[str] = []
    if not source_root.exists():
        failures.append(f"source dir missing: {source_root}")
        return False, failures, warnings

    registry = source_root / "registry"
    events = source_root / "events"

    # 1. projects registry
    projects = _load_yaml_list(registry / "projects.yml", "projects", failures)
    project_ids: set[str] = set()
    for p in projects:
        pid = p.get("id") or p.get("project_id")
        if not pid:
            failures.append("project record missing 'id' / 'project_id'")
            continue
        if pid in project_ids:
            failures.append(f"duplicate project id: {pid}")
        project_ids.add(pid)

    # 2. agents registry
    agents = _load_yaml_list(registry / "agents.yml", "agents", failures)
    agent_ids: set[str] = set()
    for a in agents:
        aid = a.get("id") or a.get("agent_id")
        if not aid:
            failures.append("agent record missing 'id' / 'agent_id'")
            continue
        if aid in agent_ids:
            failures.append(f"duplicate agent id: {aid}")
        agent_ids.add(aid)

    # 3. events
    if not events.exists():
        failures.append(f"events dir missing: {events}")
    else:
        event_files = sorted(events.glob("*.json"))
        if not event_files:
            warnings.append(f"no event files in {events}")
        for path in event_files:
            ev = _load_event(path, failures)
            if ev is None:
                continue
            et = ev.get("event_type")

            # project_id: required for everything EXCEPT AGENT_REGISTERED
            # (an agent-registration event is not a project event).
            pid = ev.get("project_id")
            if et == "AGENT_REGISTERED":
                # Optional; only validate if present
                if pid and project_ids and pid not in project_ids:
                    failures.append(
                        f"{path.name}: project_id '{pid}' not in projects registry"
                    )
            else:
                if not pid:
                    failures.append(f"{path.name}: missing required field 'project_id'")
                elif project_ids and pid not in project_ids:
                    failures.append(
                        f"{path.name}: project_id '{pid}' not in projects registry"
                    )

            # agent_id: required for everything EXCEPT PROJECT_REGISTERED
            # (a project-registration event's "agent_id" is the registering
            # agent; we allow the project_id to be reused as the agent_id
            # placeholder when the user doesn't have a primary agent yet).
            aid = ev.get("agent_id")
            if et == "PROJECT_REGISTERED":
                if not aid:
                    failures.append(f"{path.name}: missing required field 'agent_id'")
                elif agent_ids and aid not in agent_ids:
                    # Allow it to be the project_id itself (placeholder).
                    if aid != pid:
                        failures.append(
                            f"{path.name}: agent_id '{aid}' not in agents registry"
                        )
            else:
                if not aid:
                    failures.append(f"{path.name}: missing required field 'agent_id'")
                elif agent_ids and aid not in agent_ids:
                    failures.append(
                        f"{path.name}: agent_id '{aid}' not in agents registry"
                    )

            for field in ("event_type", "status", "summary"):
                if field not in ev or ev[field] in (None, ""):
                    failures.append(f"{path.name}: missing required field '{field}'")
            if not any(ev.get(f) for f in TIMESTAMP_FIELDS):
                failures.append(
                    f"{path.name}: missing timestamp (need one of {TIMESTAMP_FIELDS})"
                )
            status = ev.get("status")
            if status not in ALLOWED_STATUSES:
                failures.append(
                    f"{path.name}: status '{status}' not in {sorted(ALLOWED_STATUSES)}"
                )
            if et and et not in ALLOWED_EVENT_TYPES:
                failures.append(
                    f"{path.name}: event_type '{et}' not in {sorted(ALLOWED_EVENT_TYPES)}"
                )
            # type-specific
            if et in TYPE_REQUIRED_FIELDS:
                for field in TYPE_REQUIRED_FIELDS[et]:
                    if field not in ev or ev[field] in (None, ""):
                        failures.append(
                            f"{path.name}: {et} missing field '{field}'"
                        )

    return (len(failures) == 0), failures, warnings


# ----------------------------------------------------------------- main


def main() -> int:
    p = argparse.ArgumentParser(description="validate control tower data")
    p.add_argument(
        "--source",
        choices=("data", "examples", "both", "public-data"),
        default="data",
        help="which dataset to validate (default: data)",
    )
    p.add_argument(
        "--root",
        default=None,
        help="override repo root (default: parent of scripts/)",
    )
    args = p.parse_args()

    repo_root = Path(args.root).resolve() if args.root else HERE.parent

    sources = ("data", "examples") if args.source == "both" else (args.source,)
    overall_ok = True
    for src in sources:
        source_root = repo_root / src
        print("=" * 60)
        print(f"validate: source = {src}  ({source_root})")
        print("=" * 60)
        ok, failures, warnings = _validate_source(source_root)
        if warnings:
            print(f"WARNINGS ({len(warnings)}):")
            for w in warnings:
                print(f"  - {w}")
        if ok:
            print(f"PASS: source '{src}' valid")
        else:
            print(f"FAIL: source '{src}' has {len(failures)} issue(s)")
            for f in failures:
                print(f"  - {f}")
            overall_ok = False
    print("=" * 60)
    print("OVERALL: PASS" if overall_ok else "OVERALL: FAIL")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
