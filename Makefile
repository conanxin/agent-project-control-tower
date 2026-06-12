# Agent Project Control Tower — Makefile
# ACT-4A: add public-data publish preflight. `all` stays zero-dep and
# keeps using local data/ + examples/ (no npm). The new `publish-preflight`
# target is opt-in and is what CI will run on every push.
# ACT-6: `dashboard` builds the PUBLIC dist (uses public-data via
# apps/dashboard/package.json's prebuild hook); `dashboard-local` is
# the new opt-in for building a dist from local data/.

PYTHON ?= python3

.PHONY: help seed validate build site site-only dashboard dashboard-local test test-cli clean all reset \
        public-data public-build public-build-final publish-preflight publish-preflight-examples command-test \
        candidate candidate-fixture candidate-test export-plan-test \
        public-update-preflight public-update-test

help:
	@echo "make targets:"
	@echo "  seed               - copy examples/ into data/ (initial setup; --force overwrites)"
	@echo "  validate           - run tower.py validate (data/)"
	@echo "  build              - run tower.py build (data/ → generated/index.json + site/index.embedded.html)"
	@echo "  site               - run build_embedded_site.py only (rebuild embedded HTML)"
	@echo "  dashboard          - (ACT-6) build PUBLIC Astro dashboard at apps/dashboard/dist/"
	@echo "                       (auto-runs prebuild hook → public-data → generated/)"
	@echo "  dashboard-local    - (ACT-6) build dashboard from LOCAL data/ (opt-in, debug only)"
	@echo "  test               - run tests/smoke.py (ACT-1 acceptance)"
	@echo "  test-cli           - run tests/cli_smoke.py (ACT-2 CLI smoke, isolated temp dir)"
	@echo "  command-test       - (ACT-7B) run tests/command_generator_smoke.py (generator + alignment check)"
	@echo "  candidate          - (ACT-9B) build reviewable candidate artifact (public-data reference)"
	@echo "  candidate-fixture  - (ACT-9B) build candidate from examples/ (CI-safe)"
	@echo "  candidate-test     - (ACT-9B) run tests/candidate_artifact_smoke.py"
	@echo "  export-plan-test   - (ACT-9C) run tests/export_plan_smoke.py"
	@echo "  reset              - delete data/ and re-seed from examples/ (destructive)"
	@echo "  all                - validate + build + test + test-cli + command-test (zero deps, no npm)"
	@echo "  clean              - remove generated/ and site/index.embedded.html"
	@echo ""
	@echo "ACT-7B generator (zero-dep, stdlib only):"
	@echo "  scripts/generate_tower_command.py    print a single-line tower.py command"
	@echo "  scripts/check_template_cli_alignment.py  template ↔ tower.py drift check"
	@echo "  tests/command_generator_smoke.py      8/8 coverage incl. drift detection"
	@echo ""
	@echo "ACT-4A public-publish targets (opt-in; CI uses these):"
	@echo "  public-data        - export examples/ (sanitized seed) into public-data/"
	@echo "  public-data-real   - (ACT-6) export a redacted slice of data/ for one real project"
	@echo "                       (overrides: PROJECT / AGENT / MAX / PREFIX)"
	@echo "  public-build       - validate + build generated/index.json from public-data/"
	@echo "  publish-preflight  - public-data-real + public-build + embedded site + Astro dashboard"
	@echo "                       (ACT-6 default: builds the real-slice public dist)"

seed:
	$(PYTHON) scripts/tower.py seed --force

validate:
	$(PYTHON) scripts/tower.py validate

build:
	$(PYTHON) scripts/tower.py build

site: build
	$(PYTHON) scripts/build_embedded_site.py

# ACT-4A: same as `site` but does NOT trigger `build` first — used by
# publish-preflight, which has already produced generated/index.json
# from public-data/ and does not want a default-source rebuild to
# overwrite it.
site-only:
	$(PYTHON) scripts/build_embedded_site.py

# ACT-3B → ACT-6: build Astro dashboard.
#
# ACT-6 split this into two targets:
#
#   `dashboard`           — PUBLIC dist. Safe to deploy. Used by
#                           publish-preflight and (via npm prebuild) by
#                           Cloudflare Pages build. Runs `npm run build`
#                           in apps/dashboard/, which itself runs the
#                           prebuild hook that regenerates
#                           generated/index.json from public-data/.
#                           Does NOT depend on `build` (data) because
#                           that would race the prebuild hook.
#
#   `dashboard-local`     — LOCAL dist from data/. Opt-in for offline
#                           debug. Explicitly generates generated/ from
#                           data/ FIRST, then runs `npm run build`
#                           with the prebuild hook DISABLED
#                           (SKIP_DASHBOARD_PREBUILD=1) so data is
#                           not overwritten by public-data at build
#                           time.
#
# `make all` deliberately does NOT run either — keeping the zero-dep path.
#
# `npm run build` (in apps/dashboard) is the only command that needs
# `npm install` to have been run once.
dashboard:
	@echo "→ npm run build in apps/dashboard/ (PUBLIC, via prebuild hook)"
	cd apps/dashboard && npm run build

dashboard-local:
	@echo "→ build generated/index.json from local data/"
	$(PYTHON) scripts/tower.py build
	@echo "→ npm run build in apps/dashboard/ (LOCAL data, prebuild skipped)"
	cd apps/dashboard && SKIP_DASHBOARD_PREBUILD=1 npm run build

test:
	$(PYTHON) tests/smoke.py

test-cli:
	$(PYTHON) tests/cli_smoke.py

command-test:
	$(PYTHON) tests/command_generator_smoke.py

# ACT-9B: Level 3 prototype targets.
#
# `candidate`         — default: --source public-data (no-op reference).
#                       Safe to run any time; does NOT touch public-data/,
#                       data/, or generated/. Writes under
#                       artifacts/public-data-candidate/ (gitignored).
#
# `candidate-fixture` --source examples. CI-safe: no real data.
#
# `candidate-test`    — runs tests/candidate_artifact_smoke.py.
#                       Covers all 3 source modes + the missing-data
#                       error path that GitHub Actions hits.
#
# These targets are deliberately NOT in `make all` (they create
# artifacts/public-data-candidate/ on disk). Run them on demand.
candidate:
	$(PYTHON) scripts/build_public_data_candidate.py --source public-data --output artifacts/public-data-candidate --plan $(PUBLIC_DATA_PLAN)

candidate-fixture:
	$(PYTHON) scripts/build_public_data_candidate.py --source examples --output artifacts/public-data-candidate

candidate-test:
	$(PYTHON) tests/candidate_artifact_smoke.py

export-plan-test:
	$(PYTHON) tests/export_plan_smoke.py

# ACT-11: local public-data update preflight.
#
# `public-update-preflight` runs scripts/public_data_update_preflight.py
# which:
#   - reads config/public-data-export-plan.yml
#   - snapshots the current public-data/ state
#   - regenerates public-data/ from data/ via export_public_data.py
#   - validates and rebuilds generated/ + site/index.embedded.html
#   - runs regression checks (1-project downgrade, BookTrans Desk
#     repo misclassification, redaction FAIL > 0)
#   - writes a reviewable artifact directory under
#     artifacts/public-data-update-preflight/
#
# It does NOT git add / commit / push. The human reviews the artifact
# directory and does the commit/push by hand. See
# templates/checklists/public-data-update-preflight-checklist.md.
#
# Deliberately NOT in `make all`: this target mutates public-data/
# on disk, and the smoke test also does. The ACT-11 verification
# runs them on demand via `make public-update-preflight` and
# `make public-update-test`.
public-update-preflight:
	$(PYTHON) scripts/public_data_update_preflight.py --plan $(PUBLIC_DATA_PLAN)

public-update-test:
	$(PYTHON) tests/public_update_preflight_smoke.py

reset:
	rm -rf data generated site/index.embedded.html
	$(PYTHON) scripts/tower.py seed --force
	$(PYTHON) scripts/tower.py build

all: validate build test test-cli command-test

clean:
	rm -f generated/index.json site/index.embedded.html

# ============================================================ ACT-4A / ACT-6 / ACT-9C
# public-data: write a sanitized snapshot of examples/ into public-data/
# (default — demo seed; what ACT-4A/5 shipped).
#
# ACT-6 split this into two targets:
#
#   `public-data`        — exports examples/ (demo seed). ACT-4A default.
#                          Kept for CI to seed an empty public-data/.
#
#   `public-data-real`   — exports a redacted slice of data/ for the
#                          production dashboard. Used by ACT-6 onward
#                          to publish the live state.
#
# ACT-9C changed `public-data-real` to use a TRACKED PLAN FILE
# (`config/public-data-export-plan.yml` by default, override via
# `make public-data-real PUBLIC_DATA_PLAN=...`). The plan is the
# single source of truth for which projects and agents are
# allowed in public-data/. Hardcoded 1-project defaults were
# removed in ACT-9C because they repeatedly caused public-data
# to be silently truncated to 1 project on local rebuilds.
#
# Both targets refuse to write if redaction finds any FAIL-level secrets.

PUBLIC_DATA_PLAN ?= config/public-data-export-plan.yml
PUBLIC_DATA_MAX     ?= 50
PUBLIC_DATA_PREFIX  ?= conanxin

public-data:
	$(PYTHON) scripts/export_public_data.py --source examples --replace

public-data-real:
	@echo "→ exporting real project slice from data/ → public-data/ (via tracked plan)"
	$(PYTHON) scripts/export_public_data.py \
	    --source data \
	    --output public-data \
	    --plan $(PUBLIC_DATA_PLAN) \
	    --max-events $(PUBLIC_DATA_MAX) \
	    --repo-prefix $(PUBLIC_DATA_PREFIX) \
	    --replace

# public-build: regenerate generated/index.json + embedded HTML from
# public-data/ (NOT data/). Use this to verify the public dashboard path.
public-build:
	@echo "→ validate public-data"
	$(PYTHON) scripts/tower.py validate --source public-data
	@echo "→ build generated/index.json from public-data"
	$(PYTHON) scripts/tower.py build --source public-data

# public-build-final: same as public-build, but with a different name so
# `make` doesn't deduplicate it in the publish-preflight chain. Used as
# the LAST step of publish-preflight to overwrite whatever default-data
# build `dashboard: build` left in generated/.
public-build-final:
	@echo "→ final pass: regenerate generated/index.json from public-data"
	$(PYTHON) scripts/tower.py build --source public-data

# publish-preflight: end-to-end local verification of the public publish
# path, without actually deploying. CI runs this on every push.
#
# ACT-6: replaced the leading `public-data` step with `public-data-real`.
# Why: the public dashboard now reflects the redacted real-project slice
# of data/, not the examples/ seed. ACT-4A's `public-data` target still
# exists for seeding an empty public-data/ from examples/; ACT-6
# publishes from data/.
#
# ACT-9C: `publish-preflight` is now plan-driven (it calls
# `public-data-real` with `--plan config/public-data-export-plan.yml`).
# The local human runs this on local-hermes, which has the real `data/`.
# CI cannot run this (it has no data/ — gitignored — and the plan
# filter expects the 3 real production projects that don't exist on a
# fresh runner). CI uses `publish-preflight-examples` instead, which
# is the original ACT-4A path: examples/ → public-data/.
#
# Sequence:
#   1. public-data-real  — export data/ → public-data/ (redacted slice)
#   2. public-build      — validate public-data + regenerate generated/
#   3. site-only         — regenerate site/index.embedded.html (zero-dep
#                          public snapshot)
#   4. dashboard         — npm run build in apps/dashboard/
#                          (its prebuild hook regenerates generated/
#                          from public-data/ — idempotent with step 2)
#   5. public-build-final — final pass: regenerate generated/ from
#                          public-data/ so the working tree reflects
#                          the published source. After this target,
#                          generated/ and dist/ both correspond to
#                          public-data, which is what CF Pages serves.
publish-preflight: public-data-real public-build site-only dashboard public-build-final
	@echo ""
	@echo "==========================================================="
	@echo "PUBLISH PREFLIGHT: PASS"
	@echo "  public-data/    exported from data/ (redacted real-project slice)"
	@echo "  generated/      rebuilt from public-data"
	@echo "  site/embedded   rebuilt from public-data"
	@echo "  apps/dashboard  dist/ rebuilt from public-data"
	@echo "  (nothing deployed — ACT-4B creates the remote and pushes)"
	@echo "==========================================================="

# publish-preflight-examples — ACT-9C variant of publish-preflight for
# CI runners. Uses the original ACT-4A `public-data` target (examples/
# → public-data/) instead of `public-data-real`. Same downstream
# pipeline (validate → build → site-only → dashboard → final-build),
# but the export source is the sanitized fixture, not the local real
# data/. The local-human runbook continues to use `publish-preflight`
# (the plan-driven one above) for production refreshes.
publish-preflight-examples: public-data public-build site-only dashboard public-build-final
	@echo ""
	@echo "==========================================================="
	@echo "PUBLISH PREFLIGHT (EXAMPLES): PASS"
	@echo "  public-data/    exported from examples/ (sanitized fixture)"
	@echo "  generated/      rebuilt from public-data"
	@echo "  site/embedded   rebuilt from public-data"
	@echo "  apps/dashboard  dist/ rebuilt from public-data"
	@echo "  (CI-runner preflight — local-hermes uses `publish-preflight`"
	@echo "   with --plan and the real data/ for production refreshes.)"
	@echo "==========================================================="
