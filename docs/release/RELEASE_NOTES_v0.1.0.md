# Release Notes — Agent Project Control Tower v0.1.0

**Version:** v0.1.0  
**Release date:** 2026-06-12  
**GitHub repo:** https://github.com/conanxin/agent-project-control-tower  
**Online dashboard:** https://control-tower.conanxin.com/

---

## What this project is

A Git-backed control tower for tracking multi-agent project progress. Each agent reports events to a local `data/` store; a human or authorized primary agent reviews and exports a redacted `public-data/` slice to a Cloudflare Pages dashboard.

## Why it exists

To maintain a single source of truth for project status across multiple machines and agents, without exposing private paths, tokens, or in-progress work.

## Current architecture

| Layer | Purpose | Visibility |
|---|---|---|
| `data/` | Local event store (YAML + JSON) | Private, gitignored |
| `public-data/` | Reviewed export for dashboard | Public, tracked in git |
| `generated/` | Build artifacts (index.json, embedded HTML) | Private, gitignored |
| `apps/dashboard/` | Astro static site | Public via Cloudflare Pages |
| `config/public-data-export-plan.yml` | Export scope contract | Public, tracked in git |

## Included features

1. **Git-backed project control tower** — versioned metadata + events
2. **`data/` private local event store** — agents write here, never directly to public-data
3. **`public-data/` reviewed public export** — double-door model: human review required
4. **`config/public-data-export-plan.yml`** — tracked export scope contract
5. **`generated/index.json` build pipeline** — zero-dependency Python scripts
6. **Static embedded HTML dashboard** — `site/index.embedded.html` for offline use
7. **Astro dashboard on Cloudflare Pages** — https://control-tower.conanxin.com/
8. **Custom domain** — `control-tower.conanxin.com`
9. **`tower.py` CLI** — validate, build, seed, register-agent, register-project, report-phase, report-failure, report-review, report-handoff, report-release
10. **Command generator** — `scripts/generate_tower_command.py` for safe multi-line CLI
11. **Template alignment checker** — `scripts/check_template_cli_alignment.py`
12. **Proposed export artifact prototype** — `scripts/build_public_data_candidate.py` + `.github/workflows/proposed-export.yml`
13. **Export plan workflow** — `config/public-data-export-plan.yml`
14. **Multi-machine playbooks** — `docs/MULTI_MACHINE_SETUP.md`
15. **Public-data automation policy** — `docs/PUBLIC_DATA_AUTOMATION_POLICY.md`

## Public-data boundary

* `data/` is private and gitignored
* `public-data/` is reviewed and tracked
* `config/public-data-export-plan.yml` defines current public scope
* CI validates and can generate candidate artifacts, but does **not** mutate `public-data/`
* Agents can write `data/` but cannot automatically publish `public-data/`
* Level 5 fully automatic export is **explicitly rejected** for now

## Export plan boundary

The current plan (`config/public-data-export-plan.yml`) exports:
* 3 projects: `agent-project-control-tower`, `artvee-gallery`, `booktrans-desk`
* 2 agents: `local-hermes`, `cloud-openclaw`
* Max 50 events per project

## Proposed export artifact boundary

* Generates reviewable candidate tarballs
* CI can trigger via `workflow_dispatch`
* Does NOT auto-commit or auto-push
* Requires human review before promotion to `public-data/`

## Multi-machine validation result

* Local Hermes (notebook) — primary agent, scaffolding role
* Cloud OpenClaw (VPS) — secondary agent, long-running role
* Cross-machine onboarding trial completed (ACT-8)
* Generated-command trial validated (ACT-8B)

## Current public-data status (as of v0.1.0)

* 3 projects: `agent-project-control-tower`, `artvee-gallery`, `booktrans-desk`
* 2 agents: `local-hermes`, `cloud-openclaw`
* 24 events (cap 50 per project, newest first)
* 0 redaction FAILs, 0 WARNs

## BookTrans Desk status note (v0.1.0)

BookTrans Desk is shown as `PARTIAL` (amber) on purpose:

* **Phase**: S13 (Blocker Fixes and Manual Validation Rerun)
* **Source commit**: `16f38b6`
* **Health**: amber (real Windows desktop click-through remains `BLOCKED_MANUAL` — manual QA pending)
* **Repo**: `conanxin/booktrans-desk` (NOT `conanxin/conanxin-homepage` — ACT-6C bug class is documented and preflight now checks it)

## Public-data update workflow (v0.1.0)

v0.1.0 ships the ACT-11 preflight + ACT-12 trial as the supported way to update public-data:

1. Agent writes a `PHASE_REPORT` to local `data/` via `tower.py report-phase`.
2. Human (or local-hermes) runs `make public-update-preflight` — this regenerates the candidate public-data, then writes review artifacts to `artifacts/public-data-update-preflight/`.
3. Reviewer walks through `UPDATE_SUMMARY.md` + `PUBLIC_DATA_DIFF.md` + `REDACTION_RESULT.md` + `REVIEW_CHECKLIST.md`.
4. If everything looks correct, run `python3 scripts/export_public_data.py --plan config/public-data-export-plan.yml --replace`.
5. `git add` ONLY the changed public-data files + `site/index.embedded.html` (NEVER `git add .`).
6. Commit + push. Cloudflare Pages auto-deploys.
7. Wait 60–90s for CDN cache, then run `templates/checklists/online-verification-checklist.md`.

ACT-12 confirmed this workflow end-to-end. ACT-12 also caught one leak that ACT-11 missed: `MANIFEST.json` previously embedded the absolute local `plan_file` path — now it's repo-relative.

## Screenshots & demo assets (ACT-10B polish)

* 6 PNGs in `docs/media/v0.1.0/` covering desktop home, mobile home, timeline, agent-project-control-tower page, booktrans-desk page, and cloud-openclaw agent page.
* Captured 2026-06-12 from <https://control-tower.conanxin.com/> via Playwright + Chromium.
* Capture script lives at `/tmp/capture_v010_screenshots.py` (not committed; reproducible).
* `demo-flow.gif` is **deferred** to v0.2.0+ — static screenshots cover the visual release needs for v0.1.0.

## Known limitations

* No automatic public-data export
* `data/` remains local and gitignored
* public-data export requires human / authorized primary agent review
* Dashboard is static (no real-time, no auth)
* No database
* No login system
* No Cloudflare API automation
* Proposed export artifact is review-only

## Recommended next phase

* **ACT-12B:** second recurring update trial (long-running stability validation of the ACT-11/ACT-12 workflow)
* **ACT-13:** adoption packaging (entry-point polish for new agents / new humans cloning the repo)

## Security / privacy boundary

* `data/` contains local paths, agent metadata, and in-progress events — never exported
* `public-data/` is scanned for tokens, IPs, home paths, and `.env` references before export
* Redaction FAIL blocks export; WARN requires human judgment
* No secrets are stored in the repository
