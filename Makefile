.PHONY: dev test lint fmt typecheck clean dist help

PYTHON ?= python3
SRC     = wlanspawn tests

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

dev:  ## Install in editable mode with dev deps
	$(PYTHON) -m pip install -e ".[dev]"

test:  ## Run tests with coverage
	pytest --cov=wlanspawn --cov-report=term-missing -v

test-fast:  ## Run tests without coverage (faster)
	pytest -v -x

lint:  ## Run all linters (black + ruff + mypy)
	black --check $(SRC)
	ruff check $(SRC)
	mypy wlanspawn

fmt:  ## Auto-format code with black + ruff
	black $(SRC)
	ruff check $(SRC) --fix

typecheck:  ## Run mypy only
	mypy wlanspawn

clean:  ## Remove build/dist/cache artifacts
	rm -rf build dist *.egg-info .coverage htmlcov .pytest_cache .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

dist:  ## Build wheel and sdist
	$(PYTHON) -m build

install-local:  ## Install built wheel locally (for testing)
	pip install dist/wlanspawn-*.whl --force-reinstall

check-dist:  ## Check distribution packages
	twine check dist/*
