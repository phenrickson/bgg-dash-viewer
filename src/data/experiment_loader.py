"""
Experiment loader for loading ML experiment data from GCS.
Version-aware loader adapted from bgg-predictive-models for use in the dash viewer.
"""

import json
import logging
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import pandas as pd
from google.cloud import storage
import google.cloud.exceptions

logger = logging.getLogger(__name__)

# Default GCS bucket for experiments
DEFAULT_BUCKET_NAME = "bgg-predictive-models"
# Base prefix for experiment data (prod environment)
EXPERIMENTS_PREFIX = "prod/models/experiments"


class ExperimentLoader:
    """Efficient loader for experiment data from GCS with version support."""

    def __init__(self, bucket_name: str | None = None):
        self.bucket_name = bucket_name or os.getenv(
            "GCS_BUCKET_NAME", DEFAULT_BUCKET_NAME
        )
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(self.bucket_name)
        self.prefix = EXPERIMENTS_PREFIX

        self._metadata_cache: dict[str, Any] = {}
        self._experiments_cache: dict[str, list[dict[str, Any]]] = {}

    def list_model_types(self) -> list[str]:
        """List available model types in the experiments bucket."""
        try:
            blobs = self.bucket.list_blobs(prefix=f"{self.prefix}/", delimiter="/")

            model_types = []
            for page in blobs.pages:
                model_types.extend(
                    [
                        prefix.rstrip("/").split("/")[-1]
                        for prefix in page.prefixes
                        if not prefix.endswith("predictions/")
                    ]
                )

            return sorted(model_types)
        except Exception as e:
            logger.error(f"Error listing model types: {e}")
            return []

    def list_versions(self, model_type: str, exp_name: str) -> list[str]:
        """Discover all version directories for an experiment.

        Returns sorted list of version strings (e.g., ['v1', 'v2']).
        Falls back to [''] if no version directories exist.
        """
        base_path = f"{self.prefix}/{model_type}/{exp_name}/"
        try:
            blobs = self.bucket.list_blobs(prefix=base_path, delimiter="/")
            versions = []
            for page in blobs.pages:
                for p in page.prefixes:
                    dirname = p.rstrip("/").split("/")[-1]
                    if dirname.startswith("v") and dirname[1:].isdigit():
                        versions.append(dirname)
            if versions:
                return sorted(versions, key=lambda v: int(v[1:]))
        except Exception as e:
            logger.warning(f"Error listing versions for {exp_name}: {e}")

        return [""]

    def _get_version_path(
        self, model_type: str, exp_name: str, version: str | None = None
    ) -> str:
        """Get the path for a specific version of an experiment.

        If version is None, uses the latest available version.
        """
        base_path = f"{self.prefix}/{model_type}/{exp_name}"
        if version is None:
            versions = self.list_versions(model_type, exp_name)
            version = versions[-1] if versions else ""
        if version:
            return f"{base_path}/{version}"
        return base_path

    def list_experiments(self, model_type: str) -> list[dict[str, Any]]:
        """List experiments for a given model type with enriched metadata.

        Loads metadata for the latest version of each experiment.
        Includes version info, is_eval, is_finalized, test_through fields.
        """
        cache_key = f"experiments_{model_type}"
        if cache_key in self._experiments_cache:
            logger.debug(f"Using cached experiments for {model_type}")
            return self._experiments_cache[cache_key]

        try:
            logger.debug(f"Loading experiments for model type: {model_type}")
            experiments = []
            prefix = f"{self.prefix}/{model_type}/"

            blobs = self.bucket.list_blobs(prefix=prefix, delimiter="/")

            experiment_dirs = []
            for page in blobs.pages:
                experiment_dirs.extend(
                    [p.rstrip("/").split("/")[-1] for p in page.prefixes]
                )

            logger.debug(f"Found {len(experiment_dirs)} experiment directories")

            def load_enriched(exp_name: str) -> dict[str, Any] | None:
                try:
                    return self._load_enriched_experiment_metadata(model_type, exp_name)
                except Exception as e:
                    logger.warning(f"Failed to load metadata for {exp_name}: {e}")
                    return None

            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [
                    executor.submit(load_enriched, exp_name)
                    for exp_name in experiment_dirs
                ]

                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        experiments.append(result)

            # Sort by timestamp (newest first)
            experiments.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

            self._experiments_cache[cache_key] = experiments
            logger.debug(f"Cached {len(experiments)} experiments for {model_type}")

            return experiments

        except Exception as e:
            logger.error(f"Error listing experiments for {model_type}: {e}")
            return []

    def _load_enriched_experiment_metadata(
        self, model_type: str, exp_name: str
    ) -> dict[str, Any]:
        """Load enriched metadata for a single experiment (latest version)."""
        versions = self.list_versions(model_type, exp_name)
        latest_version = versions[-1] if versions else ""
        base_path = self._get_version_path(model_type, exp_name, latest_version)

        experiment: dict[str, Any] = {
            "full_name": exp_name,
            "experiment_name": exp_name,
            "model_type": model_type,
            "timestamp": "",
            "metrics": {},
            "parameters": {},
            "model_info": {},
            "version": latest_version,
            "versions": versions,
            "is_eval": exp_name.startswith("eval-"),
            "is_finalized": False,
            "test_through": None,
            "algorithm": None,
            "model_task": "regression",
        }

        # Load metadata.json
        try:
            blob = self.bucket.blob(f"{base_path}/metadata.json")
            content = blob.download_as_text()
            metadata = json.loads(content)
            for key, value in metadata.items():
                if key not in ["metrics", "parameters", "model_info"]:
                    experiment[key] = value
            # Extract nested metadata fields
            nested = metadata.get("metadata", {})
            experiment["test_through"] = nested.get("test_through")
            experiment["algorithm"] = nested.get("algorithm")
            experiment["model_task"] = nested.get("model_task", "regression")
        except google.cloud.exceptions.NotFound:
            pass
        except Exception as e:
            logger.warning(f"Error loading metadata for {exp_name}: {e}")

        # Check for finalized directory
        try:
            finalized_blobs = list(
                self.bucket.list_blobs(
                    prefix=f"{base_path}/finalized/", max_results=1
                )
            )
            experiment["is_finalized"] = len(finalized_blobs) > 0
        except Exception:
            pass

        # Load metrics for each dataset
        for dataset in ["train", "tune", "test"]:
            try:
                blob = self.bucket.blob(f"{base_path}/{dataset}_metrics.json")
                content = blob.download_as_text()
                experiment["metrics"][dataset] = json.loads(content)
            except google.cloud.exceptions.NotFound:
                experiment["metrics"][dataset] = {}
            except Exception:
                experiment["metrics"][dataset] = {}

        # Load parameters
        try:
            blob = self.bucket.blob(f"{base_path}/parameters.json")
            content = blob.download_as_text()
            experiment["parameters"] = json.loads(content)
        except google.cloud.exceptions.NotFound:
            pass
        except Exception as e:
            logger.warning(f"Error loading parameters for {exp_name}: {e}")

        # Load model info
        try:
            blob = self.bucket.blob(f"{base_path}/model_info.json")
            content = blob.download_as_text()
            experiment["model_info"] = json.loads(content)
        except google.cloud.exceptions.NotFound:
            pass
        except Exception as e:
            logger.warning(f"Error loading model_info for {exp_name}: {e}")

        return experiment

    def load_experiment_details(
        self, model_type: str, exp_name: str, version: str | None = None
    ) -> dict[str, Any]:
        """Load detailed experiment information including all files.

        Args:
            model_type: The model type.
            exp_name: The experiment name.
            version: Specific version to load (e.g., 'v1'). None for latest.
        """
        base_path = self._get_version_path(model_type, exp_name, version)
        cache_key = f"details_{model_type}_{exp_name}_{base_path}"
        if cache_key in self._metadata_cache:
            return self._metadata_cache[cache_key]

        try:
            details: dict[str, Any] = {}

            files_to_load = {
                "metadata": "metadata.json",
                "parameters": "parameters.json",
                "model_info": "model_info.json",
                "train_metrics": "train_metrics.json",
                "tune_metrics": "tune_metrics.json",
                "test_metrics": "test_metrics.json",
            }

            def load_file(file_info: tuple[str, str]) -> tuple[str, Any]:
                file_key, filename = file_info
                file_path = f"{base_path}/{filename}"
                try:
                    blob = self.bucket.blob(file_path)
                    content = blob.download_as_text()
                    return file_key, json.loads(content)
                except google.cloud.exceptions.NotFound:
                    return file_key, None
                except Exception as e:
                    logger.warning(f"Error loading {file_path}: {e}")
                    return file_key, None

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [
                    executor.submit(load_file, item) for item in files_to_load.items()
                ]

                for future in as_completed(futures):
                    file_key, content = future.result()
                    if content is not None:
                        details[file_key] = content

            self._metadata_cache[cache_key] = details
            return details

        except Exception as e:
            logger.error(f"Error loading experiment details for {exp_name}: {e}")
            return {}

    def load_feature_importance(
        self, model_type: str, exp_name: str, version: str | None = None
    ) -> pd.DataFrame | None:
        """Load feature importance or coefficients data for an experiment.

        Tries multiple formats: feature_importance.csv, coefficients.csv, JSON.
        For coefficients, includes uncertainty columns (std, lower_95, upper_95, significant_95).

        Args:
            model_type: The model type.
            exp_name: The experiment name.
            version: Specific version to load. None for latest.
        """
        base_path = self._get_version_path(model_type, exp_name, version)

        # Try CSV formats first
        for filename in ["feature_importance.csv", "coefficients.csv"]:
            try:
                blob = self.bucket.blob(f"{base_path}/{filename}")
                with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
                    blob.download_to_filename(tmp.name)
                    df = pd.read_csv(tmp.name)
                    os.unlink(tmp.name)
                    logger.debug(f"Loaded {filename} for {exp_name}: {df.shape}")
                    return df
            except google.cloud.exceptions.NotFound:
                continue
            except Exception as e:
                logger.warning(f"Error loading {filename} for {exp_name}: {e}")
                continue

        # Try JSON format
        try:
            blob = self.bucket.blob(f"{base_path}/feature_importance.json")
            content = blob.download_as_text()
            data = json.loads(content)
            if isinstance(data, list):
                df = pd.DataFrame(data)
                logger.debug(f"Loaded feature_importance.json for {exp_name}")
                return df
        except google.cloud.exceptions.NotFound:
            pass
        except Exception as e:
            logger.warning(f"Error loading feature_importance.json for {exp_name}: {e}")

        logger.debug(f"No feature importance found for {model_type}/{exp_name}")
        return None

    def load_predictions(
        self,
        model_type: str,
        exp_name: str,
        dataset: str = "test",
        version: str | None = None,
    ) -> pd.DataFrame | None:
        """Load predictions for an experiment.

        Args:
            model_type: The model type.
            exp_name: The experiment name.
            dataset: Dataset name ('train', 'tune', 'test').
            version: Specific version to load. None for latest.
        """
        try:
            base_path = self._get_version_path(model_type, exp_name, version)
            predictions_path = f"{base_path}/{dataset}_predictions.parquet"

            blob = self.bucket.blob(predictions_path)

            with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
                blob.download_to_filename(tmp.name)
                df = pd.read_parquet(tmp.name)
                os.unlink(tmp.name)
                return df

        except google.cloud.exceptions.NotFound:
            logger.debug(f"Predictions not found: {dataset} for {exp_name}")
            return None
        except Exception as e:
            logger.error(f"Error loading predictions for {exp_name}/{dataset}: {e}")
            return None

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._metadata_cache.clear()
        self._experiments_cache.clear()
        logger.info("Experiment loader cache cleared")


# Global singleton instance
_experiment_loader: ExperimentLoader | None = None


def get_experiment_loader(bucket_name: str | None = None) -> ExperimentLoader:
    """Get or create singleton ExperimentLoader instance."""
    global _experiment_loader
    if _experiment_loader is None:
        _experiment_loader = ExperimentLoader(bucket_name)
    return _experiment_loader
