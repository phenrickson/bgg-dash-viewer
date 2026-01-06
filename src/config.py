"""Configuration module for the BGG Dash Viewer."""

import logging
import os
from typing import Dict

import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get logger
logger = logging.getLogger(__name__)


def get_bigquery_config() -> Dict:
    """Get BigQuery configuration.

    Returns:
        Dictionary containing BigQuery configuration
    """
    # Get the absolute path to the config directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "bigquery.yaml")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    logger.info(f"Using project: {config['project']['id']}")

    # Build config with simplified structure
    return {
        "project": {
            "id": config["project"]["id"],
            "location": config["project"]["location"],
        },
        "datasets": config["datasets"],
        "storage": config["storage"],
        "tables": config["tables"],
        "raw_tables": config.get("raw_tables", {}),
    }


def get_app_config() -> Dict:
    """Get application configuration.

    Returns:
        Dictionary containing application configuration
    """
    return {
        "debug": os.getenv("DEBUG", "False").lower() in ("true", "1", "t"),
        "port": int(os.getenv("PORT", "8050")),
        "host": os.getenv("HOST", "0.0.0.0"),
        "cache_timeout": int(os.getenv("CACHE_TIMEOUT", "3600")),
    }
