VENV=.venv/bin

.PHONY: setup test lint type-check demo clean

setup:
	python3.12 -m venv .venv
	$(VENV)/pip install -q -e '.[dev]'

test:
	$(VENV)/pytest -q

test-cov:
	$(VENV)/pytest -q --cov=accessipdf --cov-report=term

lint:
	$(VENV)/ruff check accessipdf/ tests/ scripts/
	$(VENV)/ruff format --check accessipdf/ tests/ scripts/

lint-fix:
	$(VENV)/ruff check --fix accessipdf/ tests/ scripts/
	$(VENV)/ruff format accessipdf/ tests/ scripts/

type-check:
	$(VENV)/mypy accessipdf/

demo:
	$(VENV)/python -m accessipdf.demo demo_invoice.pdf

clean:
	rm -rf .venv __pycache__ *.egg-info .pytest_cache beispiele ausgang quarantaene eingang *.pdf

precommit:
	pre-commit run --all-files
