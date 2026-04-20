# BGG Dash Viewer

A Dash + Flask application for exploring BoardGameGeek data and model predictions from a BigQuery data warehouse.

## Overview

BGG Dash Viewer pairs a Flask-hosted landing page and auth layer with a Dash app that surfaces game search, predictions, similarity, and monitoring views backed by BigQuery.

## Features

- **Game Search** — card + AG Grid table views with player-count, complexity, and year filters, inline expandable details, and search-summary chips
- **New Games** — recently released games with designers, publishers, and categories
- **Upcoming Predictions** — model predictions for unreleased titles
- **Game Similarity** — find similar games via embeddings, with an Explore Embeddings tab
- **Game Ratings** — rating distributions and trends
- **Experiments** — combined experiment + version selector with synced tabs for model comparison
- **Monitoring** — BigQuery pipeline status and deployed model display
- **Auth** — Flask-Login with BigQuery-backed users, bcrypt hashing, and a registration code gate

## Installation

### Prerequisites

- Python 3.12+
- Google Cloud project with BigQuery access
- Service account credentials

### Setup

```bash
git clone https://github.com/phenrickson/bgg-dash-viewer.git
cd bgg-dash-viewer
uv sync
cp .env.example .env  # fill in BigQuery + SECRET_KEY + registration code
uv run python dash_app.py
```

## Development

### Project Structure

```text
bgg-dash-viewer/
├── dash_app.py            # Flask + Dash entry point
├── assets/                # Dash CSS
├── static/, templates/    # Flask landing page + auth pages
├── config/                # BigQuery config
├── src/
│   ├── auth/              # Flask-Login, user storage, registration
│   ├── callbacks/         # Dash callbacks (one per feature)
│   ├── components/        # Reusable Dash components (GameInfo, pills, etc.)
│   ├── data/              # BigQuery data access
│   ├── layouts/           # Page layouts (search, predictions, similarity, ...)
│   ├── theme/             # Vizro Bootstrap theming
│   ├── landing.py         # Landing page
│   └── config.py
├── docs/plans/            # Active design docs
├── tests/
├── Makefile
└── Dockerfile
```

### Common Commands

```bash
make app          # run the app locally
make test         # pytest
make format       # black
make lint         # ruff
make type-check   # mypy
make all          # format + lint + type-check + test
make build && make up   # docker build + run
```

Always use `uv run python ...` rather than system Python.

## Deployment

Containerized via `Dockerfile` and deployed to Cloud Run. Required env vars include BigQuery credentials, `SECRET_KEY`, and the registration code.

```bash
gunicorn dash_app:server
```

## License

MIT
