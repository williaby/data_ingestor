# Project B Makefile
# Development workflow automation

.PHONY: help install test lint format security clean

# Display help
help:
	@echo "Project B - Layout, OCR & Structural Extraction Engine"
	@echo ""
	@echo "Available commands:"
	@echo "  make install        Install dependencies with Poetry"
	@echo "  make install-dev    Install with dev dependencies"
	@echo "  make test           Run full test suite with coverage"
	@echo "  make test-fast      Run unit tests only (fast development loop)"
	@echo "  make test-unit      Run unit tests with coverage"
	@echo "  make test-integration  Run integration tests"
	@echo "  make test-e2e       Run end-to-end tests"
	@echo "  make lint           Run all linters (black, ruff, mypy)"
	@echo "  make format         Format code with black and ruff"
	@echo "  make security       Run security checks (bandit, safety)"
	@echo "  make clean          Remove build artifacts and caches"
	@echo "  make pre-commit     Run pre-commit hooks"
	@echo "  make verify         Run all checks (lint + security + test)"

# Installation
install:
	poetry install

install-dev:
	poetry install --with dev

# Testing
test:
	poetry run pytest -v --cov=project_b --cov-report=term-missing --cov-report=html

test-fast:
	poetry run pytest tests/unit/ -v -x --tb=short

test-unit:
	poetry run pytest tests/unit/ -v --cov=project_b --cov-report=term-missing

test-integration:
	poetry run pytest tests/integration/ -v

test-component:
	poetry run pytest tests/component/ -v

test-e2e:
	poetry run pytest tests/e2e/ -v

test-smoke:
	poetry run pytest -m smoke -v

# Code Quality
lint:
	poetry run black --check .
	poetry run ruff check .
	poetry run mypy src/project_b

format:
	poetry run black .
	poetry run ruff check --fix .

# Security
security:
	poetry run bandit -r src/project_b
	poetry run safety check

# Pre-commit
pre-commit:
	poetry run pre-commit run --all-files

pre-commit-install:
	poetry run pre-commit install

# Cleanup
clean:
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Verification (run before commit)
verify: lint security test-fast
	@echo "✅ All verification checks passed!"

# Setup (run once after cloning)
setup: install-dev pre-commit-install
	@echo "✅ Development environment setup complete!"
