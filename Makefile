# Agent Project Control Tower — Makefile
# ACT-2: tower CLI + redaction.

PYTHON ?= python3

.PHONY: help seed validate build site test test-cli clean all reset

help:
	@echo "make targets:"
	@echo "  seed      - copy examples/ into data/ (initial setup; --force overwrites)"
	@echo "  validate  - run validate.py on data/ (--source=both covers examples too)"
	@echo "  build     - run build_index.py + build_embedded_site.py"
	@echo "  site      - run build_embedded_site.py only"
	@echo "  test      - run tests/smoke.py (ACT-1 acceptance)"
	@echo "  test-cli  - run tests/cli_smoke.py (ACT-2 CLI smoke, isolated temp dir)"
	@echo "  reset     - delete data/ and re-seed from examples/ (destructive)"
	@echo "  all       - validate + build + test + test-cli"
	@echo "  clean     - remove generated/ and site/index.embedded.html"

seed:
	$(PYTHON) scripts/tower.py seed --force

validate:
	$(PYTHON) scripts/tower.py validate

build:
	$(PYTHON) scripts/tower.py build

site: build
	$(PYTHON) scripts/build_embedded_site.py

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
