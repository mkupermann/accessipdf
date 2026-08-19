VENV=.venv/bin

.PHONY: setup test lint type-check demo clean gui docker-build docker-up docker-down

setup:
	python3.12 -m venv .venv
	$(VENV)/pip install -q -e '.[dev]'

test:
	$(VENV)/pytest -q

test-cov:
	$(VENV)/pytest -q --cov=accessipdf --cov-report=term

lint:
	$(VENV)/ruff check accessipdf/ tests/ scripts/ gui/
	$(VENV)/ruff format --check accessipdf/ tests/ scripts/ gui/

lint-fix:
	$(VENV)/ruff check --fix accessipdf/ tests/ scripts/ gui/
	$(VENV)/ruff format accessipdf/ tests/ scripts/ gui/

type-check:
	$(VENV)/mypy accessipdf/ gui/

demo:
	$(VENV)/python -m accessipdf.demo demo_invoice.pdf

gui:
	$(VENV)/python scripts/run_gui.py

clean:
	rm -rf .venv __pycache__ *.egg-info .pytest_cache beispiele ausgang quarantaene eingang *.pdf

precommit:
	pre-commit run --all-files

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d accessipdf-gui

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f accessipdf-gui

playwright-install:
	$(VENV)/pip install -q playwright
	$(VENV)/python -m playwright install chromium

test-gui:
	$(VENV)/ pytest -q -m playwright tests/test_gui.py
