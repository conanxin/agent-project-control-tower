"""
validate_examples.py — pre-flight check for examples/.

Validates:
  1. examples/projects.yml parses as a list of project dicts.
  2. examples/agents.yml parses as a list of agent dicts.
  3. Every examples/events/*.json has the required fields and uses allowed
     enum values for status.
  4. Every event's project_id exists in projects registry.
  5. Every event's agent_id exists in agents registry.

Exits 0 on PASS, 1 on FAIL. Prints a human-readable summary.

Field-name notes
----------------
ACT-0 events use the schema `event_time` (a richer field name) and `phase`
(a free string like "L1", "L2-fix"). The build pipeline keeps those names so
the on-disk source-of-truth doesn't churn; the output JSON exposes
`created_at` and `phase_id` / `phase_name` aliases for downstream
consumers (including the ACT-1 build_index spec).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Make the local lib importable regardless of CWD
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lib"))

from yaml_mini import load as load_yaml  # noqa: E402

# -------------------------------------------------------------------- config

EXAMPLES_DIR = HERE.parent / "examples"
EVENTS_DIR = EXAMPLES_DIR / "events"

ALLOWED_STATUSES = {
    "ACTIVE",
    "PASS",
    "FAIL",
    "PARTIAL",
    "BLOCKED",
    "PAUSED",
    "RELEASED",
    "ARCHIVED",
}

# Required event fields. The `event_time` -> `created_at` alias is handled in
# the build layer; here we accept the on-disk name.
REQUIRED_EVENT_FIELDS = (
    "event_type",
    "project_id",
    "agent_id",
    "status",
    "summary",
)
# At least one of these must be present
TIMESTAMP_FIELDS = ("event_time", "created_at")
# For PHASE_REPORT-style events (event_type == "phase") we additionally need
# `phase` (ACT-0 schema) — the build layer splits it into phase_id/name.
PHASE_REQUIRED_FIELDS = ("phase",)

# ----------------------------------------------------------------- helpers


def _load_yaml_list(path: Path, kind: str) -> list[dict[str, Any]]:
    if not path.exists():
        print(f"  [FAIL] {kind} registry not found: {path}")
        return []
    try:
        data = load_yaml(str(path))
    except Exception as e:  # noqa: BLE001
        print(f"  [FAIL] {kind} registry parse error: {e}")
        return []
    if not isinstance(data, list):
        print(f"  [FAIL] {kind} registry must be a YAML list, got {type(data).__name__}")
        return []
    return data


def _load_event(path: Path) -> dict[str, Any] | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"  [FAIL] {path.name}: invalid JSON ({e})")
        return None
    except OSError as e:
        print(f"  [FAIL] {path.name}: cannot read ({e})")
        return None


# ----------------------------------------------------------------- main


def main() -> int:
    failures: list[str] = []
    warnings: list[str] = []

    print("=" * 60)
    print("validate_examples.py — pre-flight check")
    print("=" * 60)

    # 1. Projects registry
    print("\n[1/3] Loading projects registry …")
    projects = _load_yaml_list(EXAMPLES_DIR / "projects.yml", "projects")
    project_ids: set[str] = set()
    if projects:
        for p in projects:
            pid = p.get("id")
            if not pid:
                failures.append("project record missing 'id'")
                continue
            if pid in project_ids:
                failures.append(f"duplicate project id: {pid}")
            project_ids.add(pid)
        print(f"  ok: {len(projects)} projects, {len(project_ids)} unique ids")
    else:
        failures.append("projects registry empty or invalid")

    # 2. Agents registry
    print("\n[2/3] Loading agents registry …")
    agents = _load_yaml_list(EXAMPLES_DIR / "agents.yml", "agents")
    agent_ids: set[str] = set()
    if agents:
        for a in agents:
            aid = a.get("id")
            if not aid:
                failures.append("agent record missing 'id'")
                continue
            if aid in agent_ids:
                failures.append(f"duplicate agent id: {aid}")
            agent_ids.add(aid)
        print(f"  ok: {len(agents)} agents, {len(agent_ids)} unique ids")
    else:
        failures.append("agents registry empty or invalid")

    # 3. Events
    print("\n[3/3] Validating event files …")
    event_files = sorted(EVENTS_DIR.glob("*.json"))
    if not event_files:
        failures.append(f"no event JSON files in {EVENTS_DIR}")
    else:
        event_count = 0
        for path in event_files:
            ev = _load_event(path)
            if ev is None:
                failures.append(f"{path.name}: failed to load")
                continue
            event_count += 1
            # Required fields
            for field in REQUIRED_EVENT_FIELDS:
                if field not in ev or ev[field] in (None, ""):
                    failures.append(f"{path.name}: missing required field '{field}'")
            # Timestamp (at least one of)
            if not any(ev.get(f) for f in TIMESTAMP_FIELDS):
                failures.append(
                    f"{path.name}: missing timestamp (need one of {TIMESTAMP_FIELDS})"
                )
            # status enum
            status = ev.get("status")
            if status not in ALLOWED_STATUSES:
                failures.append(
                    f"{path.name}: status '{status}' not in {sorted(ALLOWED_STATUSES)}"
                )
            # phase-specific
            if ev.get("event_type") == "phase":
                for field in PHASE_REQUIRED_FIELDS:
                    if field not in ev or ev[field] in (None, ""):
                        failures.append(
                            f"{path.name}: PHASE_REPORT missing field '{field}'"
                        )
            # Cross-reference: project_id
            pid = ev.get("project_id")
            if pid and pid not in project_ids:
                failures.append(
                    f"{path.name}: project_id '{pid}' not in projects registry"
                )
            # Cross-reference: agent_id
            aid = ev.get("agent_id")
            if aid and aid not in agent_ids:
                failures.append(
                    f"{path.name}: agent_id '{aid}' not in agents registry"
                )
        print(f"  scanned {event_count} event file(s)")

    # Summary
    print("\n" + "=" * 60)
    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  - {w}")
    if failures:
        print(f"FAIL: {len(failures)} issue(s)")
        for f in failures:
            print(f"  - {f}")
        print("=" * 60)
        return 1
    print("PASS: all examples valid")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
