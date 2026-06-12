"""
build_public_data_candidate.py — ACT-9B Level 3 prototype.

Generate a reviewable public-data candidate artifact under
``artifacts/public-data-candidate/`` WITHOUT writing to
``public-data/``, WITHOUT committing, and WITHOUT deploying.

This script implements the Level 3 "proposed export artifact"
mode described in ``docs/PUBLIC_DATA_AUTOMATION_POLICY.md`` §3
and ``docs/PUBLIC_SCOPE_v0.1.0.md``.

Three source modes are supported:

  * ``data``       — re-export from the local gitignored ``data/``;
                     only available on a machine where ``data/``
                     exists (i.e. local-hermes). GitHub Actions
                     runners NEVER have this. This mode represents
                     the real candidate a human would then
                     manually publish via
                     ``export_public_data.py --replace``.

  * ``examples``   — fixture mode; uses the hard-coded examples
                     inside ``export_public_data.py``. Safe for
                     CI. Output is a reference candidate that
                     demonstrates the format and pipeline without
                     exposing any real state.

  * ``public-data`` — reference mode; copies the existing
                     ``public-data/`` tree verbatim into the
                     candidate directory, then re-runs redaction
                     on the copy. This produces a no-op candidate
                     used to verify the artifact machinery works
                     (downloads, tarball integrity, diff
                     computation) without changing the public
                     data source.

The script NEVER writes to ``public-data/``, ``data/``, or
``generated/``. The candidate tree lives entirely under
``artifacts/public-data-candidate/`` and is intended to be
gitignored (see ``.gitignore``). The tarball it produces is the
artifact that humans (or CI) upload for review; nothing in the
script commits or pushes.

Exit codes:

  0  PASS — candidate artifact written, no redaction FAIL
  1  FAIL — redaction FAIL on candidate, or tarball missing
  2  BAD  — invalid arguments, missing source, etc.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "lib"))

from redaction import check_payload  # noqa: E402

PUBLIC_DATA = ROOT / "public-data"
DATA = ROOT / "data"
DEFAULT_OUTPUT = ROOT / "artifacts" / "public-data-candidate"
SOURCE_CHOICES = ("data", "examples", "public-data")

# Files / directories that must NEVER end up inside the
# candidate tarball, even if they sneak in via a careless
# caller. Defense-in-depth on top of the explicit
# ``--source`` whitelist.
FORBIDDEN_TARBALL_PATHS = (
    "data",
    "generated",
    ".git",
    "node_modules",
    "__pycache__",
    ".env",
    ".venv",
    "venv",
)


# --------------------------------------------------------------------------- #
# Argument parsing
# --------------------------------------------------------------------------- #

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Build a reviewable public-data candidate artifact "
            "(Level 3 — does NOT publish)."
        ),
    )
    p.add_argument(
        "--source",
        choices=SOURCE_CHOICES,
        required=True,
        help=(
            "data (local gitignored — local-hermes only), "
            "examples (CI-safe fixture), or public-data (reference "
            "copy of the current public snapshot)."
        ),
    )
    p.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help=(
            "candidate directory (default: "
            "artifacts/public-data-candidate). The directory is "
            "wiped and recreated; nothing outside it is touched."
        ),
    )
    p.add_argument(
        "--project-id", action="append", default=None, metavar="ID",
        help="filter: only export these project IDs (repeatable).",
    )
    p.add_argument(
        "--agent-id", action="append", default=None, metavar="ID",
        help="filter: only export these agent IDs (repeatable).",
    )
    p.add_argument(
        "--max-events", type=int, default=50, metavar="N",
        help="cap events per project_id (default: 50, newest first).",
    )
    p.add_argument(
        "--repo-prefix", default="conanxin", metavar="PREFIX",
        help=(
            "rewrite 'local/<id>' to 'PREFIX/<id>' in "
            "repo/source_repo fields (default: conanxin). Set to "
            "'' to disable rewriting."
        ),
    )
    p.add_argument(
        "--tarball-name", default="public-data-candidate.tar.gz",
        help="name of the tarball inside the candidate dir.",
    )
    return p.parse_args()


# --------------------------------------------------------------------------- #
# Source-mode dispatchers
# --------------------------------------------------------------------------- #

def _build_via_export_public_data(
    out_root: Path,
    args: argparse.Namespace,
) -> dict[str, Any]:
    """Delegate to ``export_public_data.py`` and capture its
    ``MANIFEST.json``. Used for ``source=data`` and
    ``source=examples`` (the two modes the existing export
    script supports).
    """
    cmd: list[str] = [
        sys.executable,
        str(HERE / "export_public_data.py"),
        "--source", args.source,
        "--output", str(out_root),
        "--max-events", str(args.max_events),
        "--repo-prefix", args.repo_prefix,
        "--replace",
    ]
    for pid in args.project_id or []:
        cmd += ["--project-id", pid]
    for aid in args.agent_id or []:
        cmd += ["--agent-id", aid]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        raise SystemExit(
            f"export_public_data.py failed (rc={proc.returncode})"
        )
    manifest_path = out_root / "MANIFEST.json"
    if not manifest_path.exists():
        raise SystemExit(
            f"export_public_data.py did not write {manifest_path}"
        )
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _build_from_public_data_copy(
    out_root: Path,
    args: argparse.Namespace,
) -> dict[str, Any]:
    """Reference mode: copy the existing public-data/ tree into
    the candidate directory, then re-run redaction. No mutation
    of public-data/ — that copy lives only inside out_root.
    """
    if not PUBLIC_DATA.exists():
        raise SystemExit(
            f"reference mode: {PUBLIC_DATA} not found"
        )
    out_reg = out_root / "registry"
    out_evt = out_root / "events"
    out_reg.mkdir(parents=True, exist_ok=True)
    out_evt.mkdir(parents=True, exist_ok=True)

    src_reg = PUBLIC_DATA / "registry"
    src_evt = PUBLIC_DATA / "events"
    project_ids_filter = set(args.project_id) if args.project_id else None
    agent_ids_filter = set(args.agent_id) if args.agent_id else None

    # ---- copy registry (projects + agents) ----
    n_projects = 0
    n_agents = 0
    if (src_reg / "projects.yml").exists():
        projects: list[dict[str, Any]] = []
        try:
            from yaml_mini import load as _load  # type: ignore
        except Exception:
            import yaml  # type: ignore
            _load = lambda p: yaml.safe_load(  # noqa: E731
                p.read_text(encoding="utf-8")
            )
        projects = _load(src_reg / "projects.yml") or []
        if project_ids_filter is not None:
            projects = [p for p in projects if p.get("id") in project_ids_filter]
        try:
            from yaml_mini import dump as _dump  # type: ignore
        except Exception:
            import yaml  # type: ignore
            def _dump(obj: Any) -> str:
                return yaml.safe_dump(  # noqa: E731
                    obj, sort_keys=False, allow_unicode=True,
                )
        (out_reg / "projects.yml").write_text(
            _dump(projects) + "\n", encoding="utf-8",
        )
        n_projects = len(projects)
    if (src_reg / "agents.yml").exists():
        agents: list[dict[str, Any]] = []
        try:
            from yaml_mini import load as _load  # type: ignore
        except Exception:
            import yaml  # type: ignore
            _load = lambda p: yaml.safe_load(  # noqa: E731
                p.read_text(encoding="utf-8")
            )
        agents = _load(src_reg / "agents.yml") or []
        if agent_ids_filter is not None:
            agents = [a for a in agents if a.get("id") in agent_ids_filter]
        try:
            from yaml_mini import dump as _dump  # type: ignore
        except Exception:
            import yaml  # type: ignore
            def _dump(obj: Any) -> str:
                return yaml.safe_dump(  # noqa: E731
                    obj, sort_keys=False, allow_unicode=True,
                )
        (out_reg / "agents.yml").write_text(
            _dump(agents) + "\n", encoding="utf-8",
        )
        n_agents = len(agents)

    # ---- copy events (filtered) ----
    n_events = 0
    if src_evt.exists():
        for p in sorted(src_evt.glob("*.json")):
            try:
                payload = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            pid = payload.get("project_id")
            aid = payload.get("agent_id")
            if project_ids_filter is not None and pid not in project_ids_filter:
                continue
            if agent_ids_filter is not None and aid not in agent_ids_filter:
                continue
            (out_evt / p.name).write_text(
                json.dumps(
                    payload, indent=2, ensure_ascii=False, sort_keys=True,
                ) + "\n",
                encoding="utf-8",
            )
            n_events += 1

    manifest = {
        "source": "public-data-reference",
        "registry_files": sorted(
            p.name for p in out_reg.glob("*.yml")
        ),
        "event_count": n_events,
        "project_filter": (
            sorted(project_ids_filter) if project_ids_filter else None
        ),
        "agent_filter": (
            sorted(agent_ids_filter) if agent_ids_filter else None
        ),
        "max_events_per_project": args.max_events,
        "repo_prefix": args.repo_prefix,
    }
    (out_root / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "manifest": manifest,
        "n_projects": n_projects,
        "n_agents": n_agents,
        "n_events": n_events,
    }


# --------------------------------------------------------------------------- #
# Redaction scan over candidate
# --------------------------------------------------------------------------- #

def _scan_candidate(out_root: Path) -> dict[str, Any]:
    """Walk the candidate tree and re-run redaction on every
    YAML registry entry and every event JSON. Returns a
    structured report.
    """
    findings: list[dict[str, Any]] = []
    fail = 0
    warn = 0

    # registry
    reg = out_root / "registry"
    if reg.exists():
        for yml in sorted(reg.glob("*.yml")):
            try:
                from yaml_mini import load as _load  # type: ignore
            except Exception:
                import yaml  # type: ignore
                _load = lambda p: yaml.safe_load(  # noqa: E731
                    p.read_text(encoding="utf-8")
                )
            entries = _load(yml) or []
            for entry in entries:
                sev, reasons = check_payload(entry)
                for reason in reasons:
                    if sev == "FAIL":
                        fail += 1
                    else:
                        warn += 1
                    findings.append({
                        "file": str(yml.relative_to(out_root)),
                        "id": entry.get("id", "<unknown>"),
                        "severity": sev,
                        "reason": reason,
                    })
    # events
    evt = out_root / "events"
    if evt.exists():
        for p in sorted(evt.glob("*.json")):
            try:
                payload = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            sev, reasons = check_payload(payload)
            for reason in reasons:
                if sev == "FAIL":
                    fail += 1
                else:
                    warn += 1
                findings.append({
                    "file": str(p.relative_to(out_root)),
                    "id": payload.get("event_id", p.stem),
                    "severity": sev,
                    "reason": reason,
                })

    return {
        "fail": fail,
        "warn": warn,
        "pass": max(0, (fail + warn) and 1 or 1) if False else 0,  # computed below
        "findings": findings,
    }


# --------------------------------------------------------------------------- #
# Manifest diff
# --------------------------------------------------------------------------- #

def _manifest_diff(
    current: dict[str, Any] | None,
    candidate: dict[str, Any],
) -> dict[str, Any]:
    if current is None:
        return {
            "mode": "no-current-public-data",
            "current_event_count": 0,
            "candidate_event_count": candidate.get("event_count", 0),
            "delta_events": candidate.get("event_count", 0),
        }
    cur_events = current.get("event_count", 0)
    cand_events = candidate.get("event_count", 0)
    cur_files = set(current.get("registry_files", []))
    cand_files = set(candidate.get("registry_files", []))
    return {
        "mode": "diff-vs-current-public-data",
        "current_event_count": cur_events,
        "candidate_event_count": cand_events,
        "delta_events": cand_events - cur_events,
        "registry_files_added": sorted(cand_files - cur_files),
        "registry_files_removed": sorted(cur_files - cand_files),
    }


# --------------------------------------------------------------------------- #
# Report writers
# --------------------------------------------------------------------------- #

SOURCE_LABELS = {
    "data": "LOCAL GITIGNORED (real candidate for human gate)",
    "examples": "FIXTURE (CI-safe, no real data)",
    "public-data": "REFERENCE (no-op copy of current public-data)",
}

HUMAN_NEXT_ACTIONS = """\
1. Download ``public-data-candidate.tar.gz`` from the artifact
   (GitHub Actions → run → bottom-of-page Artifacts section,
   or locally from ``artifacts/public-data-candidate/``).
2. Extract and inspect ``public-data-candidate/registry/`` —
   verify each project still points to the correct
   ``repo`` and ``source_commit`` (the project identity
   review from ``PUBLIC_DATA_AUTOMATION_POLICY.md`` §6).
3. Read ``reports/MANIFEST_DIFF.md`` — confirm the
   ``delta_events`` matches what you intended.
4. Read ``reports/REDACTION_REPORT.md`` — FAIL must be 0;
   WARN must be 0 or explicitly accepted.
5. Read ``reports/REVIEW_CHECKLIST.md`` — tick every box.
6. ONLY THEN, run
   ``python scripts/export_public_data.py \\
       --source data --replace \\
       --project-id <id1> --project-id <id2> ...``
   on the local-hermes machine, review the diff, and
   ``git add public-data/`` + ``git commit`` + ``git push``
   as a normal ACT-9B-→ACT-9C workflow step.
"""


def _write_summary(
    out_root: Path,
    args: argparse.Namespace,
    manifest: dict[str, Any],
    redaction: dict[str, Any],
    diff: dict[str, Any],
    candidate_stats: dict[str, Any],
) -> None:
    p = out_root / "reports" / "CANDIDATE_SUMMARY.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Public-Data Candidate Summary")
    lines.append("")
    lines.append(f"- **generated_at**: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    lines.append(f"- **source mode**: `{args.source}` — {SOURCE_LABELS[args.source]}")
    try:
        rel_out = out_root.relative_to(ROOT)
    except ValueError:
        rel_out = out_root
    lines.append(f"- **output directory**: `{rel_out}`")
    lines.append(f"- **project filter**: {sorted(args.project_id) if args.project_id else 'all available'}")
    lines.append(f"- **agent filter**: {sorted(args.agent_id) if args.agent_id else 'all referenced'}")
    lines.append(f"- **max_events per project**: {args.max_events}")
    lines.append(f"- **repo_prefix**: `{args.repo_prefix}`")
    lines.append("")
    lines.append("## Counts")
    lines.append("")
    lines.append(f"- project_count: **{candidate_stats['n_projects']}**")
    lines.append(f"- agent_count: **{candidate_stats['n_agents']}**")
    lines.append(f"- event_count: **{manifest.get('event_count', 0)}**")
    lines.append("")
    lines.append("## Redaction")
    lines.append("")
    lines.append(f"- FAIL: **{redaction['fail']}**")
    lines.append(f"- WARN: **{redaction['warn']}**")
    lines.append(f"- findings: **{len(redaction['findings'])}**")
    lines.append("")
    lines.append("## Diff vs current public-data")
    lines.append("")
    for k, v in diff.items():
        lines.append(f"- {k}: `{v}`")
    lines.append("")
    lines.append("## ⚠️ WARNING — this candidate is NOT published")
    lines.append("")
    lines.append(
        "The candidate artifact under `artifacts/public-data-candidate/` is a "
        "**reviewable proposal only**. It has NOT been written to `public-data/`, "
        "committed to git, pushed to GitHub, or deployed to Cloudflare Pages. "
        "Publishing it requires a separate, human-gated invocation of "
        "`export_public_data.py --source data --replace` followed by an "
        "explicit `git commit` and `git push` (the ACT-9B → ACT-9C workflow)."
    )
    lines.append("")
    lines.append("## Human next actions")
    lines.append("")
    lines.append(HUMAN_NEXT_ACTIONS)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_manifest_diff(
    out_root: Path,
    diff: dict[str, Any],
) -> None:
    p = out_root / "reports" / "MANIFEST_DIFF.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Manifest Diff")
    lines.append("")
    lines.append("Comparison between the **current** public-data MANIFEST and the")
    lines.append("**candidate** MANIFEST. A delta of 0 across the board means the")
    lines.append("candidate is a no-op (reference mode).")
    lines.append("")
    for k, v in diff.items():
        lines.append(f"- {k}: `{v}`")
    lines.append("")
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_redaction_report(
    out_root: Path,
    redaction: dict[str, Any],
) -> None:
    p = out_root / "reports" / "REDACTION_REPORT.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Redaction Report")
    lines.append("")
    lines.append(f"- FAIL: **{redaction['fail']}**")
    lines.append(f"- WARN: **{redaction['warn']}**")
    lines.append(f"- findings: **{len(redaction['findings'])}**")
    lines.append("")
    if not redaction["findings"]:
        lines.append("✅ clean — no findings.")
    else:
        lines.append("## Findings")
        lines.append("")
        lines.append("| File | ID | Severity | Reason |")
        lines.append("|------|----|----|--------|")
        for f in redaction["findings"]:
            lines.append(
                f"| `{f['file']}` | `{f['id']}` | {f['severity']} | {f['reason']} |"
            )
    lines.append("")
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_review_checklist(
    out_root: Path,
    args: argparse.Namespace,
) -> None:
    p = out_root / "reports" / "REVIEW_CHECKLIST.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Public-Data Candidate — Review Checklist")
    lines.append("")
    lines.append(
        "Adapted from "
        "[`templates/checklists/public-data-automation-policy-checklist.md`]"
        "(../../templates/checklists/public-data-automation-policy-checklist.md). "
        "Tick every box before approving the candidate for publication."
    )
    lines.append("")
    lines.append("## Source identity")
    lines.append("")
    lines.append(f"- [ ] source mode is `{args.source}` and matches intent")
    lines.append("- [ ] data/ remains gitignored (NOT in this candidate tarball)")
    lines.append("- [ ] public-data/ was NOT modified by this build")
    lines.append("- [ ] generated/ was NOT modified by this build")
    lines.append("")
    lines.append("## Project identity (per project)")
    lines.append("")
    lines.append("- [ ] project_id still represents a real project")
    lines.append("- [ ] repo points to the actual code repository (e.g. conanxin/booktrans-desk)")
    lines.append("- [ ] current phase is the phase that project is genuinely in")
    lines.append("- [ ] source_commit is from that repo (not from a homepage/blog)")
    lines.append("- [ ] status / health are honest (no optimistic over-stating)")
    lines.append("- [ ] no HP-33 / homepage mis-attribution like ACT-6C")
    lines.append("")
    lines.append("## Redaction")
    lines.append("")
    lines.append("- [ ] FAIL = 0 in REDACTION_REPORT.md")
    lines.append("- [ ] WARN = 0 in REDACTION_REPORT.md, OR explicitly accepted")
    lines.append("- [ ] no token / api_key / Bearer / password / secret anywhere")
    lines.append("- [ ] no private paths (e.g. ``/home/...``, ``/Users/...``)")
    lines.append("- [ ] no raw IP addresses (the dashboard is public)")
    lines.append("")
    lines.append("## Manifest")
    lines.append("")
    lines.append("- [ ] MANIFEST_DIFF.md delta_events matches what was intended")
    lines.append("- [ ] added events are real (not test data, not stale)")
    lines.append("- [ ] removed events are intentional")
    lines.append("")
    lines.append("## Publication gate")
    lines.append("")
    lines.append("- [ ] This candidate is reviewed by the project owner")
    lines.append("- [ ] export_public_data.py --source data --replace is the next command, run by a human on local-hermes")
    lines.append("- [ ] git add public-data/ is explicit (not `git add .`)")
    lines.append("- [ ] commit message references ACT-9C (or current act id)")
    lines.append("- [ ] git push triggers Cloudflare Pages auto-deploy")
    lines.append("- [ ] online verification curl follows the ACT-0–ACT-9 precedent")
    lines.append("")
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# Tarball
# --------------------------------------------------------------------------- #

def _make_tarball(
    out_root: Path,
    tarball_path: Path,
) -> None:
    """Create a gzipped tarball of out_root. The tarball is
    named ``public-data-candidate/...`` at the top level so
    that extraction lands inside a single parent directory.

    Forbid-listed top-level entries are filtered out as
    defense-in-depth.
    """
    tarball_path.parent.mkdir(parents=True, exist_ok=True)
    if tarball_path.exists():
        tarball_path.unlink()
    with tarfile.open(tarball_path, "w:gz") as tf:
        for entry in sorted(out_root.iterdir()):
            if entry.name in FORBIDDEN_TARBALL_PATHS:
                continue
            tf.add(entry, arcname=f"public-data-candidate/{entry.name}")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main() -> int:
    args = parse_args()
    out_root = Path(args.output).resolve()
    if out_root == PUBLIC_DATA or out_root == DATA:
        print(
            f"ERROR: refuse to write candidate into protected path: {out_root}",
            file=sys.stderr,
        )
        return 2

    # ---- pre-flight: source/data/ exists check ----
    if args.source == "data" and not DATA.exists():
        print(
            "ERROR: --source data requested but data/ does not exist on this "
            "machine. GitHub Actions runners do NOT have data/. Use "
            "--source examples or --source public-data on CI.",
            file=sys.stderr,
        )
        return 2

    # ---- wipe and recreate candidate dir ----
    if out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "reports").mkdir(parents=True, exist_ok=True)

    # ---- build candidate ----
    if args.source in ("data", "examples"):
        manifest = _build_via_export_public_data(out_root, args)
        candidate_stats = {
            "n_projects": 0,
            "n_agents": 0,
            "n_events": manifest.get("event_count", 0),
        }
        # count projects/agents from the just-written registry
        proj_yml = out_root / "registry" / "projects.yml"
        agent_yml = out_root / "registry" / "agents.yml"
        if proj_yml.exists():
            try:
                from yaml_mini import load as _load  # type: ignore
            except Exception:
                import yaml  # type: ignore
                _load = lambda p: yaml.safe_load(  # noqa: E731
                    p.read_text(encoding="utf-8")
                )
            candidate_stats["n_projects"] = len(_load(proj_yml) or [])
        if agent_yml.exists():
            try:
                from yaml_mini import load as _load  # type: ignore
            except Exception:
                import yaml  # type: ignore
                _load = lambda p: yaml.safe_load(  # noqa: E731
                    p.read_text(encoding="utf-8")
                )
            candidate_stats["n_agents"] = len(_load(agent_yml) or [])
    else:  # public-data
        stats = _build_from_public_data_copy(out_root, args)
        manifest = stats["manifest"]
        candidate_stats = stats

    # ---- current public-data MANIFEST (if any) ----
    current_manifest_path = PUBLIC_DATA / "MANIFEST.json"
    current_manifest: dict[str, Any] | None = None
    if current_manifest_path.exists():
        try:
            current_manifest = json.loads(
                current_manifest_path.read_text(encoding="utf-8"),
            )
        except Exception:
            current_manifest = None

    # ---- scan candidate redaction ----
    redaction = _scan_candidate(out_root)

    # ---- diff vs current ----
    diff = _manifest_diff(current_manifest, manifest)

    # ---- write reports ----
    _write_summary(out_root, args, manifest, redaction, diff, candidate_stats)
    _write_manifest_diff(out_root, diff)
    _write_redaction_report(out_root, redaction)
    _write_review_checklist(out_root, args)

    # ---- tarball ----
    tarball_path = out_root / args.tarball_name
    _make_tarball(out_root, tarball_path)
    if not tarball_path.exists():
        print(f"ERROR: tarball not written: {tarball_path}", file=sys.stderr)
        return 1

    # ---- final report ----
    print(f"build_public_data_candidate.py — source={args.source} → {out_root}")
    print(f"  projects: {candidate_stats['n_projects']}")
    print(f"  agents:   {candidate_stats['n_agents']}")
    print(f"  events:   {manifest.get('event_count', 0)}")
    print(f"  redaction: FAIL={redaction['fail']} WARN={redaction['warn']}")
    print(f"  tarball:  {tarball_path}")
    print()
    print("WARNING: candidate is reviewable only. NOT published, NOT committed, NOT pushed.")
    if redaction["fail"] > 0:
        print("REFUSING: redaction FAIL must be 0 for Level 3 prototype.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
