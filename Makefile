# Agent Project Control Tower — Makefile
# ACT-4A: add public-data publish preflight. `all` stays zero-dep and
# keeps using local data/ + examples/ (no npm). The new `publish-preflight`
# target is opt-in and is what CI will run on every push.

PYTHON ?= python3

.PHONY: help seed validate build site site-only dashboard test test-cli clean all reset \
        public-data public-build public-build-final publish-preflight

help:
	@echo "make targets:"
	@echo "  seed               - copy examples/ into data/ (initial setup; --force overwrites)"
	@echo "  validate           - run tower.py validate (data/)"
	@echo "  build              - run tower.py build (data/ → generated/index.json + site/index.embedded.html)"
	@echo "  site               - run build_embedded_site.py only (rebuild embedded HTML)"
	@echo "  dashboard          - (ACT-3A) build Astro dashboard at apps/dashboard/dist/"
	@echo "  test               - run tests/smoke.py (ACT-1 acceptance)"
	@echo "  test-cli           - run tests/cli_smoke.py (ACT-2 CLI smoke, isolated temp dir)"
	@echo "  reset              - delete data/ and re-seed from examples/ (destructive)"
	@echo "  all                - validate + build + test + test-cli (zero deps, no npm)"
	@echo "  clean              - remove generated/ and site/index.embedded.html"
	@echo ""
	@echo "ACT-4A public-publish targets (opt-in; CI uses these):"
	@echo "  public-data        - export a sanitized snapshot into public-data/"
	@echo "  public-build       - validate + build generated/index.json from public-data/"
	@echo "  publish-preflight  - public-data + public-build + embedded site + Astro dashboard"
	@echo "                       (this is what CI runs; never auto-deploy)"

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

# ACT-3B: build polished Astro dashboard. Requires `npm install` (one-time).
# `make all` deliberately does NOT run this — keeping the zero-dep path.
# `dashboard` depends on `build` because Astro's `tower-data.ts` imports
# `generated/index.json` at build time. The dependency ensures the file
# exists regardless of how `dashboard` is invoked (locally or in CI).
dashboard: build
	@echo "→ npm run build in apps/dashboard/"
	cd apps/dashboard && npm run build

test:
	$(PYTHON) tests/smoke.py

test-cli:
	$(PYTHON) tests/cli_smoke.py

reset:
	rm -rf data generated site/index.embedded.html
	$(PYTHON) scripts/tower.py seed --force
	$(PYTHON) scripts/tower.py build

all: validate build test test-cli

clean:
	rm -f generated/index.json site/index.embedded.html

# ============================================================ ACT-4A
# public-data: write a sanitized snapshot of examples/ (or data/) into
# public-data/ for the public dashboard to consume. Refuses to write
# if redaction finds any FAIL-level secrets.
public-data:
	$(PYTHON) scripts/export_public_data.py --source examples

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
# Sequence:
#   1. export a sanitized snapshot into public-data/
#   2. validate public-data
#   3. regenerate generated/index.json from public-data
#   4. regenerate site/index.embedded.html (zero-dep public snapshot)
#   5. build the Astro dashboard dist/ (requires `npm install` once)
#   6. (last) re-run public-build so the working tree's generated/
#      reflects public-data (not data/, which `dashboard: build` rewrote
#      in step 5). After this target, generated/ and dist/ both
#      correspond to public-data, which is what gets uploaded/published.
publish-preflight: public-data public-build site-only dashboard public-build-final
	@echo ""
	@echo "==========================================================="
	@echo "PUBLISH PREFLIGHT: PASS"
	@echo "  public-data/    populated from examples/"
	@echo "  generated/      rebuilt from public-data"
	@echo "  site/embedded   rebuilt from public-data"
	@echo "  apps/dashboard  dist/ rebuilt from public-data"
	@echo "  (nothing deployed — ACT-4B creates the remote and pushes)"
	@echo "==========================================================="
