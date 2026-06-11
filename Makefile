# Agent Project Control Tower — Makefile
# ACT-1: zero-dep local data flow prototype.

PYTHON ?= python3

.PHONY: help validate build site clean all test

help:
	@echo "make targets:"
	@echo "  validate  - run validate_examples.py (pre-flight check)"
	@echo "  build     - run build_index.py to generate generated/index.json"
	@echo "  site      - run build_embedded_site.py to produce site/index.embedded.html"
	@echo "  test      - run tests/smoke.py (asserts build output)"
	@echo "  all       - validate + build + site + test"
	@echo "  clean     - remove generated/ and site/index.embedded.html"

validate:
	$(PYTHON) scripts/validate_examples.py

build:
	$(PYTHON) scripts/build_index.py

site: build
	$(PYTHON) scripts/build_embedded_site.py

test:
	$(PYTHON) tests/smoke.py

all: validate build site test

clean:
	rm -f generated/index.json site/index.embedded.html
