"""
export_public_data.py — copy a sanitized snapshot of the control tower
data into public-data/ for the public dashboard to consume.

This is intentionally small: read the source dataset, run every text
field through the redaction checker, and write the result to
public-data/registry/ and public-data/events/.

Why a separate tool?
--------------------
- The public dashboard must never accidentally see real tokens, IP
  addresses, or local home paths.
- `data/` (real run) is gitignored; `examples/` is sanitized but is the
  illustrative seed, not the live state.
- `public-data/` is the dataset GitHub Pages / Cloudflare Pages will
  actually serve. It must be:
    * tracked in git (so CI rebuilds are reproducible)
    * validated by the same redaction rules as a regular event write
    * easy to refresh (one CLI call)

ACT-6 additions
---------------
- `--project-id` / `--agent-id`: filter the export to a specific
  subset. Without these, ALL projects/agents/events in the source
  are exported (the original ACT-4A behaviour).
- `--max-events N`: cap per-project event count (default 50, newest
  first by created_at). Useful for "first real project" exports
  where you want the public dashboard to show recent activity only.
- `--replace`: wipe public-data/{registry,events} before writing.
  Default (no `--replace`) merges: existing files that are not in
  the new export are kept. Use `--replace` to ensure the public
  dataset is exactly what you just exported.
- `--repo-prefix PREFIX`: rewrite repo fields of the form
  `local/<project-id>` to `PREFIX/<project-id>`. This is the
  ACT-6 redaction pattern: data/ uses `local/<id>` as a placeholder
  to avoid leaking the real on-disk path; the public version uses
  the actual GitHub org. Default: `conanxin`.

ACT-9C additions
----------------
- `--plan PATH`: read export scope (source/output/projects/agents)
  from a tracked plan YAML (default:
  `config/public-data-export-plan.yml`). MUTUALLY EXCLUSIVE with
  `--project-id` and `--agent-id` — mixing the two is a hard error,
  on purpose, because the plan file is the single source of truth
  for what the public dashboard is allowed to show. The MANIFEST
  records the plan file path and name so reviewers can verify
  provenance.

Usage
-----
    # ACT-4A: copy from examples/ to public-data/ (default; demo seed)
    python scripts/export_public_data.py

    # ACT-4A: copy from the local real control tower (data/)
    python scripts/export_public_data.py --source data

    # ACT-6: copy only one project's public subset, rewrite repo prefix
    python scripts/export_public_data.py \
        --source data \
        --output public-data \
        --project-id agent-project-control-tower \
        --agent-id local-hermes \
        --max-events 20 \
        --repo-prefix conanxin \
        --replace

    # ACT-9C: use a tracked plan (preferred; the only way `make
    # publish-preflight` invokes the script)
    python scripts/export_public_data.py \
        --plan config/public-data-export-plan.yml \
        --replace

    # dry-run — show what would change, do not write
    python scripts/export_public_data.py --dry-run

Exit codes
----------
    0  success
    1  redaction FAIL — refused to write
    2  I/O / structural error
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "lib"))

from redaction import check_text  # noqa: E402

PUBLIC_DATA = ROOT / "public-data"
REGISTRY_FIELDS_TO_SCAN: tuple[str, ...] = (
    "id", "type", "display_name", "operator", "machine", "name", "repo",
    "location", "category", "description",
)
EVENT_FIELDS_TO_SCAN: tuple[str, ...] = (
    "summary", "phase_name", "next", "design_reason",
    "impact_analysis", "source_repo", "release_url", "reason",
    "failure_reason",
)


def _scan_value(value: Any) -> tuple[str, str]:
    """Recursively scan a JSON-like value; return worst (severity, reason)."""
    worst = ("PASS", "")
    if isinstance(value, str):
        sev, why = check_text(value)
        if sev == "FAIL":
            return sev, why
        if sev == "WARN" and worst[0] == "PASS":
            worst = (sev, why)
    elif isinstance(value, dict):
        for v in value.values():
            s, w = _scan_value(v)
            if s == "FAIL":
                return s, w
            if s == "WARN" and worst[0] == "PASS":
                worst = (s, w)
    elif isinstance(value, list):
        for v in value:
            s, w = _scan_value(v)
            if s == "FAIL":
                return s, w
            if s == "WARN" and worst[0] == "PASS":
                worst = (s, w)
    return worst


def _scan_registry(name: str, entries: list[dict[str, Any]]) -> list[str]:
    """Return list of WARN/FAIL messages found across a registry list."""
    msgs: list[str] = []
    for e in entries:
        for f in REGISTRY_FIELDS_TO_SCAN:
            v = e.get(f)
            sev, why = _scan_value(v)
            if sev in ("FAIL", "WARN"):
                msgs.append(f"  [{sev}] {name}.{f}: {why}")
    return msgs


def _scan_event(path: Path, payload: dict[str, Any]) -> list[str]:
    msgs: list[str] = []
    for f in EVENT_FIELDS_TO_SCAN:
        v = payload.get(f)
        sev, why = _scan_value(v)
        if sev in ("FAIL", "WARN"):
            msgs.append(f"  [{sev}] {path.name}#{f}: {why}")
    return msgs


def _load_plan_file(plan_path: Path) -> dict[str, Any]:
    """Load an ACT-9C export plan YAML.

    Tries :mod:`yaml_mini` first (ships with the project, zero-dep);
    falls back to PyYAML if installed. Returns a plain dict.

    Hard-fails with a clear error if the file cannot be parsed —
    a malformed plan is the kind of thing we want humans to notice
    immediately, not silently ignore.
    """
    try:
        from yaml_mini import load as _load  # type: ignore
    except Exception:
        try:
            import yaml  # type: ignore
            def _load(p: Path) -> Any:
                return yaml.safe_load(p.read_text(encoding="utf-8"))
        except Exception:
            print(
                "ERROR: no YAML loader available to read --plan. "
                "Install PyYAML or ensure scripts/lib/yaml_mini.py is importable.",
                file=sys.stderr,
            )
            raise SystemExit(2)

    try:
        data = _load(plan_path)
    except Exception as e:
        print(f"ERROR: cannot parse plan file {plan_path}: {e}", file=sys.stderr)
        raise SystemExit(2)

    if not isinstance(data, dict):
        print(
            f"ERROR: --plan {plan_path} must be a YAML mapping at the top level, "
            f"got {type(data).__name__}.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    return data


def _filter_projects(entries: list[dict[str, Any]], project_ids: set[str] | None) -> list[dict[str, Any]]:
    if not project_ids:
        return list(entries)
    return [e for e in entries if e.get("id") in project_ids]


def _filter_agents(entries: list[dict[str, Any]], agent_ids: set[str] | None) -> list[dict[str, Any]]:
    if not agent_ids:
        return list(entries)
    return [e for e in entries if e.get("id") in agent_ids]


def _filter_events(
    events: list[tuple[Path, dict[str, Any]]],
    project_ids: set[str] | None,
    agent_ids: set[str] | None,
) -> list[tuple[Path, dict[str, Any]]]:
    out: list[tuple[Path, dict[str, Any]]] = []
    for p, payload in events:
        pid = payload.get("project_id")
        aid = payload.get("agent_id")
        if project_ids and pid not in project_ids:
            continue
        if agent_ids and aid not in agent_ids:
            continue
        out.append((p, payload))
    return out


def _cap_events_per_project(
    events: list[tuple[Path, dict[str, Any]]],
    max_events: int,
) -> list[tuple[Path, dict[str, Any]]]:
    """Keep at most max_events per project_id, newest first by created_at."""
    if max_events <= 0:
        return events
    by_pid: dict[str | None, list[tuple[Path, dict[str, Any]]]] = {}
    for p, payload in events:
        by_pid.setdefault(payload.get("project_id"), []).append((p, payload))
    out: list[tuple[Path, dict[str, Any]]] = []
    for pid, items in by_pid.items():
        items.sort(key=lambda kv: kv[1].get("created_at") or "", reverse=True)
        kept = items[:max_events]
        if len(items) > max_events:
            print(f"  cap: project={pid} kept {len(kept)}/{len(items)} events (--max-events {max_events})")
        out.extend(kept)
    # Re-sort by created_at descending for stable output ordering
    out.sort(key=lambda kv: kv[1].get("created_at") or "", reverse=True)
    return out


def _rewrite_repo(value: Any, repo_prefix: str) -> Any:
    """Rewrite repo fields of the form 'local/<project-id>' to '<prefix>/<project-id>'.

    This is the ACT-6 redaction: data/ uses 'local/' as a safe placeholder
    for the on-disk path; the public version uses the actual GitHub org.
    Recurses into dicts/lists. Idempotent on already-public values.
    """
    if isinstance(value, str):
        if value.startswith("local/"):
            return f"{repo_prefix}/{value[len('local/'):]}"
        return value
    if isinstance(value, dict):
        return {k: _rewrite_repo(v, repo_prefix) for k, v in value.items()}
    if isinstance(value, list):
        return [_rewrite_repo(v, repo_prefix) for v in value]
    return value


def _infer_agents_from_events(
    events: list[tuple[Path, dict[str, Any]]],
) -> set[str]:
    """Return the set of agent_id values that appear in any event payload."""
    return {payload.get("agent_id") for _, payload in events if payload.get("agent_id")}


def main() -> int:
    p = argparse.ArgumentParser(
        description="Export a sanitized snapshot for the public dashboard",
    )
    p.add_argument(
        "--source", choices=("examples", "data"), default="examples",
        help="which dataset to export (default: examples — sanitized seed)",
    )
    p.add_argument(
        "--output", default=None,
        help="output directory (default: public-data)",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="show what would be scanned, do not write",
    )
    p.add_argument(
        "--project-id", action="append", default=None, metavar="ID",
        help="filter: only export these project IDs (repeatable). "
             "If omitted, all projects in source are exported.",
    )
    p.add_argument(
        "--agent-id", action="append", default=None, metavar="ID",
        help="filter: only export these agent IDs (repeatable). "
             "If omitted, agents referenced by exported events are exported.",
    )
    p.add_argument(
        "--max-events", type=int, default=50, metavar="N",
        help="cap events per project_id (default: 50, newest first)",
    )
    p.add_argument(
        "--replace", action="store_true",
        help="wipe output/{registry,events} before writing (default: merge)",
    )
    p.add_argument(
        "--repo-prefix", default="conanxin", metavar="PREFIX",
        help="rewrite 'local/<project-id>' to 'PREFIX/<project-id>' in repo/source_repo "
             "fields (default: conanxin). Set to '' to disable rewriting.",
    )
    p.add_argument(
        "--plan", default=None, metavar="PATH",
        help="ACT-9C: read export scope (source/output/projects/agents) from a "
             "tracked plan YAML. MUTUALLY EXCLUSIVE with --project-id and "
             "--agent-id (mixing the two is a hard error).",
    )
    args = p.parse_args()

    # ---- ACT-9C: load --plan, enforce mutual exclusion ----
    plan_path: Path | None = None
    plan_data: dict[str, Any] = {}
    if args.plan:
        if args.project_id:
            print(
                "ERROR: --plan and --project-id are mutually exclusive. "
                "List the project IDs in the plan file instead.",
                file=sys.stderr,
            )
            return 2
        if args.agent_id:
            print(
                "ERROR: --plan and --agent-id are mutually exclusive. "
                "List the agent IDs in the plan file instead.",
                file=sys.stderr,
            )
            return 2
        plan_path = Path(args.plan).resolve()
        if not plan_path.exists():
            print(f"ERROR: --plan file not found: {plan_path}", file=sys.stderr)
            return 2
        plan_data = _load_plan_file(plan_path)
        if not plan_data.get("projects"):
            print(
                f"ERROR: --plan {plan_path} has no `projects:` list "
                "(empty or missing). Refusing to export an unscoped slice.",
                file=sys.stderr,
            )
            return 2
        # Apply plan values (CLI defaults still win for flags the plan
        # doesn't specify, e.g. --replace / --max-events / --repo-prefix).
        if "source" in plan_data:
            args.source = plan_data["source"]
        if "output" in plan_data and not args.output:
            args.output = plan_data["output"]
        args.project_id = list(plan_data["projects"])
        if "agents" in plan_data and plan_data["agents"]:
            args.agent_id = list(plan_data["agents"])
        print(f"export_public_data.py — plan={plan_path}")
        if "name" in plan_data:
            print(f"  plan.name: {plan_data['name']}")
        print(f"  plan schema_version: {plan_data.get('schema_version', '(none)')}")
        if "policy" in plan_data:
            pol = plan_data["policy"]
            print(f"  plan.policy.level: {pol.get('level', '(none)')}")
            if pol.get("ci_may_commit") or pol.get("ci_may_push"):
                print(
                    "  [WARN] plan.policy says CI may commit/push — but "
                    "export_public_data.py is a local-only tool. The hard "
                    "rail is enforced by the tool, not by the plan.",
                    file=sys.stderr,
                )

    src_root = ROOT / args.source
    if not src_root.exists():
        print(
            f"ERROR: source not found: {src_root}\n"
            f"  --source {args.source} was {'from plan' if plan_data else 'CLI default'}. "
            f"If you intended the local real control tower, run `make seed` first "
            f"or pass --source data explicitly.",
            file=sys.stderr,
        )
        return 2

    out_root = Path(args.output).resolve() if args.output else PUBLIC_DATA
    out_reg = out_root / "registry"
    out_evt = out_root / "events"

    project_ids = set(args.project_id) if args.project_id else None
    agent_ids = set(args.agent_id) if args.agent_id else None

    print(f"export_public_data.py — source={args.source} → {out_root}")
    if project_ids:
        print(f"  filter: project_id in {sorted(project_ids)}")
    if agent_ids:
        print(f"  filter: agent_id in {sorted(agent_ids)}")
    print(f"  cap: max_events={args.max_events} per project (newest first)")
    print(f"  mode: {'replace' if args.replace else 'merge'}")
    print(f"  repo-prefix: '{args.repo_prefix}' (set to '' to disable rewrite)")
    print()

    # ---- YAML loader (try stdlib yaml_mini first, fall back to PyYAML) ----
    try:
        from yaml_mini import load as _load  # type: ignore
    except Exception:
        try:
            import yaml  # type: ignore
            _load = lambda p: yaml.safe_load(p.read_text(encoding="utf-8"))  # noqa: E731
        except Exception:
            print(
                "  [FAIL] no YAML loader available — install PyYAML or "
                "ensure scripts/lib/yaml_mini.py is importable",
                file=sys.stderr,
            )
            return 2

    all_warns: list[str] = []
    all_fails: list[str] = []

    # ---- load + filter + rewrite projects ----
    src_projects = src_root / "registry" / "projects.yml"
    projects_out: list[dict[str, Any]] = []
    if src_projects.exists():
        entries = _load(src_projects) or []
        entries = _filter_projects(entries, project_ids)
        if args.repo_prefix:
            entries = [_rewrite_repo(e, args.repo_prefix) for e in entries]
        msgs = _scan_registry("projects.yml", entries)
        for m in msgs:
            if "[FAIL]" in m:
                all_fails.append(m)
            else:
                all_warns.append(m)
        projects_out = entries
        print(f"  registry/projects.yml: {len(entries)} entries (after filter), "
              f"{len(msgs)} finding(s)")
    else:
        print(f"  [WARN] projects.yml not in source — skipping")

    # ---- load + filter events first, so we know which agents to keep ----
    src_evt_dir = src_root / "events"
    events_in: list[tuple[Path, dict[str, Any]]] = []
    if src_evt_dir.exists():
        for p in sorted(src_evt_dir.glob("*.json")):
            try:
                payload = json.loads(p.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"  [WARN] cannot parse {p.name}: {e}", file=sys.stderr)
                continue
            events_in.append((p, payload))

    events_filtered = _filter_events(events_in, project_ids, agent_ids)
    events_filtered = _cap_events_per_project(events_filtered, args.max_events)
    if args.repo_prefix:
        events_filtered = [
            (p, _rewrite_repo(payload, args.repo_prefix))
            for p, payload in events_filtered
        ]

    for p, payload in events_filtered:
        msgs = _scan_event(p, payload)
        for m in msgs:
            if "[FAIL]" in m:
                all_fails.append(m)
            else:
                all_warns.append(m)
    print(f"  events/: {len(events_filtered)} files (after filter+cap), "
          f"out of {len(events_in)} in source")

    # ---- agents: keep only those that appear in exported events,
    #      or all if --agent-id is set (then we filter below) ----
    src_agents = src_root / "registry" / "agents.yml"
    agents_out: list[dict[str, Any]] = []
    if src_agents.exists():
        entries = _load(src_agents) or []
        if args.agent_id:
            # user explicitly named agents — honour their list
            entries = _filter_agents(entries, agent_ids)
        else:
            # default: keep agents referenced by exported events
            referenced = _infer_agents_from_events(events_filtered)
            entries = _filter_agents(entries, referenced)
        msgs = _scan_registry("agents.yml", entries)
        for m in msgs:
            if "[FAIL]" in m:
                all_fails.append(m)
            else:
                all_warns.append(m)
        agents_out = entries
        print(f"  registry/agents.yml: {len(entries)} entries (after filter), "
              f"{len(msgs)} finding(s)")
    else:
        print(f"  [WARN] agents.yml not in source — skipping")

    print()
    print(f"redaction summary: FAIL={len(all_fails)}, WARN={len(all_warns)}")
    for m in all_fails:
        print(m)
    for m in all_warns:
        print(m)

    if all_fails:
        print()
        print("REFUSING to write public-data/ — redaction FAILs above.")
        return 1

    if args.dry_run:
        print()
        print("DRY RUN — no files written.")
        return 0

    # ---- write ----
    if args.replace and out_root.exists():
        # Only wipe registry/ and events/ — leave MANIFEST.json to be
        # regenerated below. Other top-level files in public-data/ are
        # not touched (defensive: the directory is shared with ACT-5B
        # etc. and we never want to accidentally nuke them).
        for sub in (out_reg, out_evt):
            if sub.exists():
                shutil.rmtree(sub)
        print(f"  --replace: wiped {out_reg} and {out_evt}")

    out_reg.mkdir(parents=True, exist_ok=True)
    out_evt.mkdir(parents=True, exist_ok=True)

    # write projects.yml (filtered + rewritten YAML)
    if projects_out:
        # Use yaml_mini for writing (it ships with the project) to stay
        # zero-dep. Fall back to the shared ACT-9B yaml_dumper
        # helper, which wraps PyYAML with the ACT-8B 4-space hotfix
        # and has a pure-stdlib fallback for environments where
        # neither yaml_mini has dump() nor PyYAML is installed
        # (e.g. vanilla GitHub Actions runners).
        try:
            from yaml_mini import dump as _dump  # type: ignore
        except Exception:
            from yaml_dumper import dumper as _dd
            _dump = _dd()
        (out_reg / "projects.yml").write_text(
            _dump(projects_out) + "\n", encoding="utf-8"
        )
        print(f"  wrote {out_reg/'projects.yml'} ({len(projects_out)} entries)")

    if agents_out:
        # Use yaml_mini for writing (it ships with the project) to stay
        # zero-dep. Fall back to PyYAML + ACT-8B hotfix via the
        # shared ACT-9B yaml_dumper helper, which is the same code
        # path build_public_data_candidate.py uses. The shared
        # helper also has a pure-stdlib fallback so the script
        # works in vanilla GitHub Actions runners where neither
        # yaml_mini has dump() nor PyYAML is installed.
        try:
            from yaml_mini import dump as _dump  # type: ignore
        except Exception:
            from yaml_dumper import dumper as _dd
            _dump = _dd()
        (out_reg / "agents.yml").write_text(
            _dump(agents_out) + "\n", encoding="utf-8"
        )
        print(f"  wrote {out_reg/'agents.yml'} ({len(agents_out)} entries)")

    for src_path, payload in events_filtered:
        (out_evt / src_path.name).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if events_filtered:
        print(f"  wrote {out_evt}/ ({len(events_filtered)} event files)")

    # ---- manifest ----
    manifest = {
        "source": args.source,
        "registry_files": sorted(p.name for p in out_reg.glob("*.yml")),
        "event_count": len(list(out_evt.glob("*.json"))),
        "project_filter": sorted(project_ids) if project_ids else None,
        "agent_filter": sorted(agent_ids) if agent_ids else None,
        "max_events_per_project": args.max_events,
        "repo_prefix": args.repo_prefix,
    }
    if plan_path is not None:
        manifest["plan_file"] = str(plan_path)
        if "name" in plan_data:
            manifest["plan_name"] = plan_data["name"]
        if "schema_version" in plan_data:
            manifest["plan_schema_version"] = plan_data["schema_version"]
    (out_root / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"  wrote {out_root}/MANIFEST.json")
    print()
    print("OK — public-data refreshed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
