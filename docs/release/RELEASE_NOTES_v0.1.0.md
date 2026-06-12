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

## Current public-data status

* 3 projects
* 2 agents
* 22 events
* 0 redaction FAILs
* 0 WARNs

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

* **ACT-10B:** GitHub release polish / screenshots / demo GIF
* **ACT-11:** Public-data update ergonomics (faster manual refresh workflow)

## Security / privacy boundary

* `data/` contains local paths, agent metadata, and in-progress events — never exported
* `public-data/` is scanned for tokens, IPs, home paths, and `.env` references before export
* Redaction FAIL blocks export; WARN requires human judgment
* No secrets are stored in the repository
