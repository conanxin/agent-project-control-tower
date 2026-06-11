# Agent Project Control Tower — Makefile
# ACT-3A: add `dashboard` target (Astro build). `all` stays zero-dep.

PYTHON ?= python3

.PHONY: help seed validate build site dashboard test test-cli clean all reset

help:
	@echo "make targets:"
	@echo "  seed       - copy examples/ into data/ (initial setup; --force overwrites)"
	@echo "  validate   - run tower.py validate (data/)"
	@echo "  build      - run tower.py build (data/ → generated/index.json + site/index.embedded.html)"
	@echo "  site       - run build_embedded_site.py only (rebuild embedded HTML)"
	@echo "  dashboard  - (ACT-3A) build Astro dashboard at apps/dashboard/dist/"
	@echo "  test       - run tests/smoke.py (ACT-1 acceptance)"
	@echo "  test-cli   - run tests/cli_smoke.py (ACT-2 CLI smoke, isolated temp dir)"
	@echo "  reset      - delete data/ and re-seed from examples/ (destructive)"
	@echo "  all        - validate + build + test + test-cli (zero deps, no npm)"
	@echo "  clean      - remove generated/ and site/index.embedded.html"

seed:
	$(PYTHON) scripts/tower.py seed --force

validate:
	$(PYTHON) scripts/tower.py validate

build:
	$(PYTHON) scripts/tower.py build

site: build
	$(PYTHON) scripts/build_embedded_site.py

# ACT-3A: build Astro dashboard. Requires `npm install` (one-time).
# `make all` deliberately does NOT run this — keeping the zero-dep path.
dashboard:
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
