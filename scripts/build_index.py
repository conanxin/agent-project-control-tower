"""
build_index.py — generate the dashboard's data layer.

Reads:
  <source>/registry/projects.yml
  <source>/registry/agents.yml
  <source>/events/*.json

Writes:
  generated/index.json

The output schema is described in detail in docs/MVP_PLAN.md and
docs/ARCHITECTURE.md.

--source {data,examples}  default: data
"""
from __future__ import annotations

import argparse
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
OUT = ROOT / "generated" / "index.json"

SCHEMA_VERSION = "0.2"

# Health can come from the event's own `health` field (preferred) or be
# derived from `status` if missing.
HEALTH_FROM_STATUS: dict[str, str] = {
    "PASS": "green",
    "FAIL": "red",
    "BLOCKED": "red",
    "PARTIAL": "yellow",
    "PAUSED": "gray",
    "SKIPPED": "gray",
    "ACTIVE": "green",
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


def _load_events(events_dir: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not events_dir.exists():
        return events
    for p in sorted(events_dir.glob("*.json")):
        with open(p, "r", encoding="utf-8") as f:
            events.append(json.load(f))
    return events


def _ts(event: dict[str, Any]) -> str:
    """Get the timestamp string for an event, preferring created_at then event_time."""
    return event.get("created_at") or event.get("event_time") or ""


def _project_record(
    project: dict[str, Any], events: list[dict[str, Any]]
) -> dict[str, Any]:
    pid = project.get("id") or project.get("project_id")
    pevents = sorted(
        [e for e in events if e.get("project_id") == pid],
        key=_ts,
    )
    last = pevents[-1] if pevents else None
    last_status = (last or {}).get("status") or project.get("status", "ACTIVE")
    last_health = (last or {}).get("health") or HEALTH_FROM_STATUS.get(last_status, "gray")

    topics = project.get("topics") or []
    category = topics[0] if topics else "uncategorized"

    return {
        "project_id": pid,
        "name": project.get("name") or project.get("display_name") or pid,
        "repo": project.get("repo") or project.get("source_repo"),
        "location": project.get("location")
        or project.get("scope")
        or project.get("home_machine")
        or "unknown",
        "category": category,
        "current_status": last_status,
        "current_health": last_health,
        "current_phase_id": (last or {}).get("phase_id"),
        "current_phase_name": (last or {}).get("phase_name") or (last or {}).get("phase_id"),
        "last_agent_id": (last or {}).get("agent_id"),
        "last_event_at": _ts(last) if last else None,
        "last_event_type": (last or {}).get("event_type"),
        "last_summary": (last or {}).get("summary"),
        "next": (last or {}).get("next"),
        "event_count": len(pevents),
    }


def _agent_record(
    agent: dict[str, Any], events: list[dict[str, Any]]
) -> dict[str, Any]:
    aid = agent.get("id") or agent.get("agent_id")
    aevents = [e for e in events if e.get("agent_id") == aid]
    aevents.sort(key=_ts)
    last = aevents[-1] if aevents else None
    caps = agent.get("capabilities") or []
    role = agent.get("role") or (caps[0] if caps else agent.get("type", "unknown"))
    return {
        "agent_id": aid,
        "name": agent.get("name") or agent.get("display_name") or aid,
        "machine": agent.get("machine", "unknown"),
        "role": role,
        "last_event_at": _ts(last) if last else None,
        "last_project_id": (last or {}).get("project_id"),
        "last_event_type": (last or {}).get("event_type"),
        "event_count": len(aevents),
    }


def _timeline(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """All events sorted newest first."""
    out: list[dict[str, Any]] = []
    for e in sorted(events, key=_ts, reverse=True):
        out.append(
            {
                "event_id": e.get("event_id"),
                "event_type": e.get("event_type"),
                "project_id": e.get("project_id"),
                "agent_id": e.get("agent_id"),
                "phase_id": e.get("phase_id"),
                "phase_name": e.get("phase_name"),
                "status": e.get("status"),
                "health": e.get("health"),
                "summary": e.get("summary"),
                "next": e.get("next"),
                "created_at": _ts(e),
            }
        )
    return out


def build(source: str = "data", root: Path | None = None) -> dict[str, Any]:
    if source not in ("data", "examples"):
        raise ValueError(f"source must be 'data' or 'examples', got {source!r}")
    base = root or ROOT
    src_root = base / source
    projects_raw = _load_yaml(src_root / "registry" / "projects.yml")
    agents_raw = _load_yaml(src_root / "registry" / "agents.yml")
    events = _load_events(src_root / "events")

    project_records = [_project_record(p, events) for p in projects_raw]
    agent_records = [_agent_record(a, events) for a in agents_raw]
    timeline = _timeline(events)

    health_counter: Counter[str] = Counter(
        p["current_health"] for p in project_records
    )
    blocked_count = sum(
        1 for e in events if e.get("event_type") == "BLOCK"
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "source": source,
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
    p = argparse.ArgumentParser(description="build dashboard data layer")
    p.add_argument(
        "--source",
        choices=("data", "examples"),
        default="data",
        help="which dataset to read (default: data)",
    )
    p.add_argument(
        "--output",
        default=None,
        help="output path (default: generated/index.json)",
    )
    p.add_argument(
        "--root",
        default=None,
        help="override repo root (default: parent of scripts/)",
    )
    args = p.parse_args()

    root = Path(args.root).resolve() if args.root else None
    data = build(args.source, root=root)
    out = Path(args.output).resolve() if args.output else (root or ROOT) / "generated" / "index.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    s = data["summary"]
    print(f"build_index.py — source={args.source}")
    try:
        rel = out.relative_to(root or ROOT)
    except ValueError:
        rel = out
    print(f"  wrote {rel}")
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
