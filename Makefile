PYTHON ?= python3
APP_MODULE ?= app.main:app
HOST ?= 0.0.0.0
PORT ?= 8000

.PHONY: help install install-dev test lint format typecheck dev check clean

help:
	@printf '%s\n' \
		'AI Speech Backend development commands' \
		'' \
		'Targets:' \
		'  install      Install runtime dependencies' \
		'  install-dev  Install runtime and development dependencies' \
		'  test         Run the unittest suite' \
		'  lint         Run ruff checks' \
		'  format       Format code with ruff' \
		'  typecheck    Run mypy checks' \
		'  dev          Start the FastAPI development server' \
		'  check        Run the local verification suite' \
		'  clean        Remove Python cache files'

install:
	$(PYTHON) -m pip install -e .

install-dev:
	$(PYTHON) -m pip install -e '.[dev]'

test:
	PYTHONPATH=. $(PYTHON) -m unittest discover -s tests -v

lint:
	$(PYTHON) -m ruff check app tests

format:
	$(PYTHON) -m ruff format app tests

typecheck:
	$(PYTHON) -m mypy app tests

dev:
	$(PYTHON) -m uvicorn $(APP_MODULE) --host $(HOST) --port $(PORT) --reload

check: test

clean:
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
