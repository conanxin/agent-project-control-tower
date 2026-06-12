# Changelog

## v0.1.0 — 2026-06-12

### Highlights

* Git-backed multi-agent project control tower
* Public Cloudflare Pages dashboard with custom domain
* Reviewed public-data export model (double-door: data/ → public-data/)
* Tracked export plan workflow (`config/public-data-export-plan.yml`)
* Multi-machine agent onboarding validated (local-hermes + cloud-openclaw)
* Command generator for safe multi-line CLI commands
* Proposed export artifact prototype with CI workflow
* Public-data automation policy documented

### Included phases

ACT-0 through ACT-9C

### Public dashboard

* https://control-tower.conanxin.com/

### Public data scope

* 3 projects
* 2 agents
* 22 events

### Known limitations

* No automatic public-data export — human/authorized primary agent review required
* `data/` remains local and gitignored
* Dashboard is static (no real-time updates, no auth)
* No database — flat YAML + JSON files
* No login system
* No Cloudflare API automation
* Proposed export artifact is review-only, does not auto-commit or auto-push
