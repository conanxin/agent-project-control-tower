"""
build_index.py — generate the dashboard's data layer.

Reads:
  examples/projects.yml
  examples/agents.yml
  examples/events/*.json

Writes:
  generated/index.json

Output schema (ACT-1 contract):

{
  "schema_version": "0.1",
  "generated_at": "<ISO timestamp>",
  "summary": {
    "project_count": int,
    "agent_count":   int,
    "event_count":   int,
    "green_count":   int,
    "yellow_count":  int,
    "red_count":     int,
    "blocked_count": int
  },
  "projects": [ { ... see ProjectRecord below ... } ],
  "agents":   [ { ... see AgentRecord   below ... } ],
  "timeline": [ { ... see TimelineEntry below ... } ]
}

ProjectRecord
-------------
{
  "project_id":        str,
  "name":              str,
  "repo":              str,
  "location":          "local" | "cloud" | "mixed",
  "category":          str (from topics[0] or "uncategorized"),
  "current_status":    str (last phase status or registry status),
  "current_health":    "green" | "yellow" | "red" | "gray",
  "current_phase_id":  str | null,
  "current_phase_name": str | null,
  "last_agent_id":     str | null,
  "last_event_at":     str | null,
  "last_summary":      str | null,
  "next":              str | null,
  "event_count":       int
}

AgentRecord
-----------
{
  "agent_id":       str,
  "name":           str,
  "machine":        "local" | "cloud" | "ci",
  "role":           str (from capabilities[0] or type),
  "last_event_at":  str | null,
  "last_project_id": str | null,
  "event_count":    int
}

TimelineEntry
-------------
{
  "event_id":     str,
  "project_id":   str,
  "agent_id":     str,
  "phase_id":     str | null,
  "phase_name":   str | null,
  "status":       str,
  "summary":      str,
  "created_at":   str (alias of event_time)
}
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lib"))

from yaml_mini import load as load_yaml  # noqa: E402

ROOT = HERE.parent
EXAMPLES = ROOT / "examples"
EVENTS_DIR = EXAMPLES / "events"
OUT = ROOT / "generated" / "index.json"

SCHEMA_VERSION = "0.1"

# Health derivation table — matches docs/DATA_MODEL.md §4
HEALTH_FROM_STATUS = {
    "PASS": "green",
    "FAIL": "red",
    "BLOCKED": "red",
    "PARTIAL": "yellow",
    "PAUSED": "gray",
    "SKIPPED": "gray",
    "ACTIVE": "green",  # registry status
    "RELEASED": "green",
    "ARCHIVED": "gray",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_yaml(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = load_yaml(str(path))
    return data if isinstance(data, list) else []


def _load_events() -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for p in sorted(EVENTS_DIR.glob("*.json")):
        with open(p, "r", encoding="utf-8") as f:
            events.append(json.load(f))
    return events


def _split_phase(phase: str | None) -> tuple[str | None, str | None]:
    """Split a phase string like 'L1' / 'L2-fix' / 'C1' into
    (phase_id, phase_name).

    Convention used in ACT-0 examples:
      phase_id   = the raw phase token (e.g. "L1", "L2-fix")
      phase_name = same value, with underscores converted to spaces and
                   each token capitalised for human display
    """
    if not phase:
        return None, None
    pid = phase
    pretty = phase.replace("-", " ").replace("_", " ").strip()
    if pretty:
        pretty = " ".join(w.capitalize() for w in pretty.split())
    else:
        pretty = phase
    return pid, pretty


def _project_record(
    project: dict[str, Any], events: list[dict[str, Any]]
) -> dict[str, Any]:
    # Sort events for this project by event_time ascending
    pevents = sorted(
        [e for e in events if e.get("project_id") == project.get("id")],
        key=lambda e: e.get("event_time") or e.get("created_at") or "",
    )
    last = pevents[-1] if pevents else None
    last_status = (last or {}).get("status") or project.get("status", "ACTIVE")
    health = HEALTH_FROM_STATUS.get(last_status, "gray")

    phase_id, phase_name = _split_phase((last or {}).get("phase"))

    topics = project.get("topics") or []
    category = topics[0] if topics else "uncategorized"

    return {
        "project_id": project.get("id"),
        "name": project.get("name"),
        "repo": project.get("repo"),
        "location": project.get("scope") or project.get("home_machine") or "unknown",
        "category": category,
        "current_status": last_status,
        "current_health": health,
        "current_phase_id": phase_id,
        "current_phase_name": phase_name,
        "last_agent_id": (last or {}).get("agent_id"),
        "last_event_at": (last or {}).get("event_time")
        or (last or {}).get("created_at"),
        "last_summary": (last or {}).get("summary"),
        "next": (last or {}).get("next"),
        "event_count": len(pevents),
    }


def _agent_record(
    agent: dict[str, Any], events: list[dict[str, Any]]
) -> dict[str, Any]:
    aevents = [e for e in events if e.get("agent_id") == agent.get("id")]
    aevents.sort(key=lambda e: e.get("event_time") or e.get("created_at") or "")
    last = aevents[-1] if aevents else None
    caps = agent.get("capabilities") or []
    role = caps[0] if caps else agent.get("type", "unknown")
    return {
        "agent_id": agent.get("id"),
        "name": agent.get("display_name") or agent.get("id"),
        "machine": agent.get("machine", "unknown"),
        "role": role,
        "last_event_at": (last or {}).get("event_time")
        or (last or {}).get("created_at"),
        "last_project_id": (last or {}).get("project_id"),
        "event_count": len(aevents),
    }


def _timeline(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """All events sorted by event_time descending (newest first)."""
    sorted_events = sorted(
        events,
        key=lambda e: e.get("event_time") or e.get("created_at") or "",
        reverse=True,
    )
    out: list[dict[str, Any]] = []
    for e in sorted_events:
        phase_id, phase_name = _split_phase(e.get("phase"))
        out.append(
            {
                "event_id": e.get("event_id"),
                "project_id": e.get("project_id"),
                "agent_id": e.get("agent_id"),
                "phase_id": phase_id,
                "phase_name": phase_name,
                "status": e.get("status"),
                "summary": e.get("summary"),
                "created_at": e.get("event_time") or e.get("created_at"),
            }
        )
    return out


def build() -> dict[str, Any]:
    projects_raw = _load_yaml(EXAMPLES / "projects.yml")
    agents_raw = _load_yaml(EXAMPLES / "agents.yml")
    events = _load_events()

    project_records = [_project_record(p, events) for p in projects_raw]
    agent_records = [_agent_record(a, events) for a in agents_raw]
    timeline = _timeline(events)

    health_counter: Counter[str] = Counter(
        p["current_health"] for p in project_records
    )
    # A project is "blocked" only when an explicit `block` event exists.
    # Phase FAIL with a `blocker` hint does NOT count — that's a normal
    # failure, the agent is free to retry.
    blocked_count = sum(
        1 for e in events if e.get("event_type") == "block"
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "summary": {
            "project_count": len(project_records),
            "agent_count": len(agent_records),
            "event_count": len(events),
            "green_count": health_counter.get("green", 0),
            "yellow_count": health_counter.get("yellow", 0),
            "red_count": health_counter.get("red", 0),
            "blocked_count": blocked_count,
        },
        "projects": project_records,
        "agents": agent_records,
        "timeline": timeline,
    }


def main() -> int:
    print("build_index.py — generating dashboard data layer …")
    if not EXAMPLES.exists():
        print(f"  [FAIL] examples dir missing: {EXAMPLES}")
        return 1
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    s = data["summary"]
    print(f"  wrote {OUT.relative_to(ROOT)}")
    print(
        f"  {s['project_count']} projects, "
        f"{s['agent_count']} agents, "
        f"{s['event_count']} events"
    )
    print(
        f"  health: green={s['green_count']} yellow={s['yellow_count']} "
        f"red={s['red_count']} blocked={s['blocked_count']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
