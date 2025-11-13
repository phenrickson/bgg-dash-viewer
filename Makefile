.PHONY: help install format lint type-check test run clean all

# Default target
help:
	@echo "Available targets:"
	@echo "  install     - Install dependencies including dev dependencies"
	@echo "  format      - Format code with black and sort imports with ruff"
	@echo "  lint        - Run ruff linter"
	@echo "  type-check  - Run mypy type checker"
	@echo "  test        - Run pytest tests"
	@echo "  app         - Run the Dash application"
	@echo "  clean       - Clean up cache files"
	@echo "  all         - Run format, lint, type-check, and test"

# Install dependencies
install:
	uv sync --dev

# Format code
format:
	uv run black src/ tests/
	uv run ruff check --fix src/ tests/

# Lint code
lint:
	uv run ruff check src/ tests/

# Type check
type-check:
	uv run mypy src/

# Run tests
test:
	uv run pytest

# Run the application
app:
	uv run -m src.app

# Clean cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .cache-data

# Run all checks
all: format lint type-check test
