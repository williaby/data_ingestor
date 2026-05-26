.PHONY: help install setup test test-fast test-pre-commit test-pr test-performance test-smoke test-with-timing lint format security clean

# Default target
.DEFAULT_GOAL := help

# Python interpreter
PYTHON := python3.12
UV     := uv

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install all dependencies (including extras)
	$(UV) sync --all-extras

setup: install ## Complete development setup
	$(UV) run pre-commit install
	$(UV) run python src/utils/encryption.py
	@echo "Development environment ready!"

test: ## Run tests with coverage (parallelized)
	$(UV) run pytest -v -n auto --cov=src --cov-report=html --cov-report=term-missing

test-serial: ## Run tests without parallelization (for debugging)
	$(UV) run pytest -v --cov=src --cov-report=html --cov-report=term-missing

test-fast: ## Run fast tests for development (< 10 seconds, parallelized)
	$(UV) run pytest tests/unit/ -m "not slow and not performance and not stress" -n auto --maxfail=3 --tb=short

test-integration: ## Run integration tests (parallelized, excludes slow)
	$(UV) run pytest tests/integration/ -m "not slow and not performance" -n auto -v

test-integration-all: ## Run ALL integration tests (includes slow tests)
	$(UV) run pytest tests/integration/ -n auto -v

test-pre-commit: ## Run pre-commit validation tests (< 30 seconds, parallelized)
	$(UV) run pytest tests/unit/ tests/integration/ -m "not slow and not performance and not stress and not contract" -n auto --maxfail=5

test-pr: ## Run PR validation tests (< 2 minutes, parallelized)
	$(UV) run pytest -m "not slow and not performance and not stress" -n auto --maxfail=10

test-performance: ## Run performance tests only
	$(UV) run pytest tests/performance/ -m "performance or stress" --tb=line

test-smoke: ## Run smoke tests for basic functionality
	$(UV) run pytest tests/unit/ -m "smoke or fast" -n auto --maxfail=1 -x

test-with-timing: ## Run tests with detailed timing analysis (serial for accurate timing)
	$(UV) run pytest --durations=20 --tb=short

test-debug: ## Run tests in debug mode (serial, verbose, stop on first failure)
	$(UV) run pytest -xvs --tb=short --pdb

lint: ## Run linting checks
	$(UV) run ruff format --check .
	$(UV) run ruff check .
	$(UV) run mypy src
	markdownlint **/*.md
	yamllint .

format: ## Format code
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

security: ## Run security checks
	$(UV) run pip-audit
	$(UV) run bandit -r src

dev: ## Start development environment with all services
	docker-compose -f docker-compose.zen-vm.yaml up -d
	@echo "Development environment started!"
	@echo "- Gradio UI: http://192.168.1.205:7860"
	@echo "- Zen MCP Server: http://192.168.1.205:3000"
	@echo "- External Qdrant Dashboard: http://192.168.1.16:6333/dashboard"

pre-commit: ## Run all pre-commit hooks manually
	$(UV) run pre-commit run --all-files

lint-docs: ## Lint documentation files with Claude Code commands
	@echo "Use Claude Code slash commands for document linting:"
	@echo "  /project:lint-doc docs/planning/exec.md"
	@echo "  /project:fix-links docs/planning/exec.md"
	@echo "  /project:validate-frontmatter docs/planning/exec.md"

clean: ## Clean build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	rm -rf .coverage htmlcov coverage.xml
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -rf dist build *.egg-info
