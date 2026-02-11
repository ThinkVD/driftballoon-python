.PHONY: install test test-integration test-all lint format ci build clean publish-check publish-test publish help

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install SDK in editable mode with dev deps
	@test -d $(VENV) || python3 -m venv $(VENV)
	$(PIP) install -e ".[dev]"

test: ## Run unit tests (no backend required)
	$(PYTEST) -m "not integration" -v

test-integration: ## Run integration tests (requires running backend)
	$(PYTEST) -m integration -v

test-all: ## Run all tests
	$(PYTEST) -v

lint: ## Lint with ruff
	$(RUFF) check .

format: ## Format with ruff
	$(RUFF) format .

ci: lint test ## Run lint + test (mirrors CI)

build: clean ## Build sdist and wheel
	$(PYTHON) -m build

clean: ## Remove build artifacts and caches
	rm -rf dist/ build/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true

publish-check: test build ## Unit tests → build → verify wheel installs and imports
	@echo "--- Verifying wheel in temporary venv ---"
	@TMPDIR=$$(mktemp -d) && \
	python3 -m venv "$$TMPDIR/venv" && \
	"$$TMPDIR/venv/bin/pip" install --quiet dist/*.whl && \
	"$$TMPDIR/venv/bin/python" -c "from driftballoon import DriftBalloon, __version__; print(f'OK  driftballoon=={__version__}')" && \
	rm -rf "$$TMPDIR" && \
	echo "--- publish-check passed ---"

publish-test: publish-check ## Publish to TestPyPI
	$(PYTHON) -m twine upload --repository testpypi dist/*

publish: publish-check ## Publish to PyPI (production)
	$(PYTHON) -m twine upload dist/*
