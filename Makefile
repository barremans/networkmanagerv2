# Makefile
# Beschrijving: Development shortcuts
# Applicatie: networkmanager
# Versie: 1.0.0
# Auteur: Barremans

# Makefile voor networkmanager

.PHONY: install test lint format clean run build

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

lint:
	flake8 app helpers utils i18n tests
	mypy app helpers utils i18n

format:
	black app helpers utils i18n tests

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf build/ dist/ .pytest_cache/

run:
	python app/main.py

build:
	python setup.py sdist bdist_wheel
