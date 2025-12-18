.PHONY: help install format lint type-check test app clean all build up down

# Default target
help:
	@echo "Available targets:"
	@echo "  install      - Install dependencies including dev dependencies"
	@echo "  format       - Format code with black and sort imports with ruff"
	@echo "  lint         - Run ruff linter"
	@echo "  type-check   - Run mypy type checker"
	@echo "  test         - Run pytest tests"
	@echo "  app          - Run the Dash application locally"
	@echo "  clean        - Clean up cache files"
	@echo "  all          - Run format, lint, type-check, and test"
	@echo "  build        - Build Docker image"
	@echo "  up           - Start Docker container"
	@echo "  down         - Stop Docker container"

# Install dependencies
install:
	uv sync --dev

# Format code
format:
	uv run black dash_app.py src/ tests/
	uv run ruff check --fix dash_app.py src/ tests/

# Lint code
lint:
	uv run ruff check dash_app.py src/ tests/

# Type check
type-check:
	uv run mypy dash_app.py src/

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
build:
	docker build -t bgg-dash-viewer .

up:
	@docker run -d --name bgg-dash-viewer -p 8080:8080 --env-file .env \
		-v "${HOME}/.config/gcloud:/root/.config/gcloud:ro" \
		-e GOOGLE_APPLICATION_CREDENTIALS=/root/.config/gcloud/application_default_credentials.json \
		bgg-dash-viewer
	@echo ""
	@echo "Container started! Access the app at:"
	@echo "  Landing page:  http://localhost:8080/"
	@echo "  Game Search:   http://localhost:8080/app/game-search"
	@echo "  Predictions:   http://localhost:8080/app/upcoming-predictions"
	@echo "  New Games:     http://localhost:8080/app/new-games"
	@echo "  Game Ratings:  http://localhost:8080/app/game-ratings"
	@echo ""
	@echo "Stop with: make down"

down:
	-docker stop bgg-dash-viewer
	@echo "Container stopped."
