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

Usage
-----
    # default: copy from examples/ to public-data/
    python scripts/export_public_data.py

    # or: copy from the local real control tower (data/)
    python scripts/export_public_data.py --source data

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
    args = p.parse_args()

    src_root = ROOT / args.source
    if not src_root.exists():
        print(f"ERROR: source not found: {src_root}", file=sys.stderr)
        return 2

    out_root = Path(args.output).resolve() if args.output else PUBLIC_DATA
    out_reg = out_root / "registry"
    out_evt = out_root / "events"

    print(f"export_public_data.py — source={args.source} → {out_root}")
    print()

    # ---- registries ----
    # Prefer the stdlib-only yaml_mini shipped in scripts/lib/.
    # Fall back to PyYAML only if it's installed (rare; we don't add it
    # to the project on purpose). Either way, this block never raises
    # ModuleNotFoundError.
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

    for name in ("projects.yml", "agents.yml"):
        src = src_root / "registry" / name
        if not src.exists():
            print(f"  [WARN] {name} not in source — skipping")
            continue
        entries = _load(src) or []
        msgs = _scan_registry(name, entries)
        for m in msgs:
            if "[FAIL]" in m:
                all_fails.append(m)
            else:
                all_warns.append(m)
        print(f"  registry/{name}: {len(entries)} entries, "
              f"{len(msgs)} finding(s)")
        if not args.dry_run:
            out_reg.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, out_reg / name)

    # ---- events ----
    src_evt = src_root / "events"
    if src_evt.exists():
        ev_files = sorted(src_evt.glob("*.json"))
        for src in ev_files:
            try:
                payload = json.loads(src.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"  [WARN] cannot parse {src.name}: {e}", file=sys.stderr)
                continue
            msgs = _scan_event(src, payload)
            for m in msgs:
                if "[FAIL]" in m:
                    all_fails.append(m)
                else:
                    all_warns.append(m)
            print(f"  events/{src.name}: "
                  f"{len(msgs)} finding(s)")
            if not args.dry_run:
                out_evt.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, out_evt / src.name)
    else:
        print("  [WARN] no events/ in source — skipping")

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

    # ---- write a manifest ----
    manifest = {
        "source": args.source,
        "registry_files": sorted(p.name for p in out_reg.glob("*.yml")),
        "event_count": len(list(out_evt.glob("*.json"))),
    }
    (out_root / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"  wrote {out_root}/MANIFEST.json: {manifest}")
    print()
    print("OK — public-data refreshed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
