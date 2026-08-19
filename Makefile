VENV=.venv/bin

.PHONY: setup test

setup:
	python3.12 -m venv .venv
	$(VENV)/pip install -q -e '.[dev]'

test:
	$(VENV)/pytest -q
