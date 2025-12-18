.PHONY: help install format lint type-check test run clean all docker-build docker-run docker-test docker-clean

# Default target
help:
	@echo "Available targets:"
	@echo "  install      - Install dependencies including dev dependencies"
	@echo "  format       - Format code with black and sort imports with ruff"
	@echo "  lint         - Run ruff linter"
	@echo "  type-check   - Run mypy type checker"
	@echo "  test         - Run pytest tests"
	@echo "  app          - Run the Dash application"
	@echo "  clean        - Clean up cache files"
	@echo "  all          - Run format, lint, type-check, and test"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-run   - Run Docker container locally"
	@echo "  docker-test  - Build and test Docker container"
	@echo "  docker-clean - Clean up Docker images and containers"

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
	uv run python dash_app.py

# Clean cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .cache-data

# Run all checks
all: format lint type-check test

# Docker commands
docker-build:
	docker build -t bgg-dash-viewer .

docker-run:
	docker run -p 8080:8080 --env-file .env bgg-dash-viewer

docker-test: docker-build
	@echo "Testing Docker build..."
	docker run --rm bgg-dash-viewer python -c "import dash_app; print('Docker build successful!')"

docker-clean:
	docker rmi bgg-dash-viewer 2>/dev/null || true
	docker system prune -f
