# BGG Dash Viewer

A Dash-based viewer for exploring BoardGameGeek data warehouse.

## Overview

BGG Dash Viewer is a web application built with Dash that provides an interactive interface for exploring and searching through BoardGameGeek board game data stored in a BigQuery data warehouse.

## Features

- Advanced game search with multiple filtering options
- Interactive visualizations of game data
- Detailed game information pages
- Responsive design for desktop and mobile

## Installation

### Prerequisites

- Python 3.12 or higher
- Access to a Google Cloud project with BigQuery
- Service account credentials with BigQuery access

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/bgg-dash-viewer.git
cd bgg-dash-viewer
```

2. Create a virtual environment using UV:
```bash
uv venv
```

3. Activate the virtual environment:
```bash
# On Windows
.venv\Scripts\activate

# On macOS/Linux
source .venv/bin/activate
```

4. Install dependencies:
```bash
uv sync
```

5. Copy the example environment file and update it with your settings:
```bash
cp .env.example .env
```

6. Run the application:
```bash
python -m src.app
```

## Development

### Project Structure

```
bgg-dash-viewer/
├── config/                # Configuration files
│   └── bigquery.yaml      # BigQuery configuration
├── src/                   # Source code
│   ├── assets/            # Static assets (CSS, images)
│   ├── components/        # Reusable Dash components
│   ├── layouts/           # Page layouts
│   ├── callbacks/         # Dash callbacks
│   ├── data/              # Data handling
│   └── app.py             # Main application entry point
└── tests/                 # Tests
```

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
# Format code with black
black .

# Lint code with ruff
ruff check .
```

## Deployment

The application can be deployed to various platforms:

### Local Development Server

```bash
python -m src.app
```

### Production Deployment with Gunicorn

```bash
gunicorn src.app:server
```

## License

MIT
