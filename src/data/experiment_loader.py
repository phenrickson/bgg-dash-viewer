"""
Experiment loader for loading ML experiment data from GCS.
Simplified version adapted from bgg-predictive-models for use in the dash viewer.
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
    """Efficient loader for experiment data from GCS."""

    def __init__(self, bucket_name: str | None = None):
        """Initialize the experiment loader.

        Args:
            bucket_name: GCS bucket name. Defaults to bgg-predictive-models.
        """
        self.bucket_name = bucket_name or os.getenv(
            "GCS_BUCKET_NAME", DEFAULT_BUCKET_NAME
        )
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(self.bucket_name)
        self.prefix = EXPERIMENTS_PREFIX

        # Cache for experiment metadata
        self._metadata_cache: dict[str, Any] = {}
        self._experiments_cache: dict[str, list[dict[str, Any]]] = {}

    def list_model_types(self) -> list[str]:
        """List available model types in the experiments bucket.

        Returns:
            List of model type names (e.g., catboost-complexity, ridge-rating).
        """
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

    def list_experiments(self, model_type: str) -> list[dict[str, Any]]:
        """List experiments for a given model type with enriched metadata.

        Args:
            model_type: The model type (e.g., 'catboost-complexity').

        Returns:
            List of experiment dictionaries with metrics and parameters.
        """
        cache_key = f"experiments_{model_type}"
        if cache_key in self._experiments_cache:
            logger.debug(f"Using cached experiments for {model_type}")
            return self._experiments_cache[cache_key]

        try:
            logger.debug(f"Loading experiments for model type: {model_type}")
            experiments = []
            prefix = f"{self.prefix}/{model_type}/"

            # List all experiment directories
            blobs = self.bucket.list_blobs(prefix=prefix, delimiter="/")

            experiment_dirs = []
            for page in blobs.pages:
                experiment_dirs.extend(
                    [p.rstrip("/").split("/")[-1] for p in page.prefixes]
                )

            logger.debug(f"Found {len(experiment_dirs)} experiment directories")

            # Load enriched metadata for each experiment in parallel
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

            # Cache the results
            self._experiments_cache[cache_key] = experiments
            logger.debug(f"Cached {len(experiments)} experiments for {model_type}")

            return experiments

        except Exception as e:
            logger.error(f"Error listing experiments for {model_type}: {e}")
            return []

    def _get_experiment_version_path(self, model_type: str, exp_name: str) -> str:
        """Get the versioned path for an experiment.

        Most experiments use v1 directory structure.

        Args:
            model_type: The model type.
            exp_name: The experiment name.

        Returns:
            The base path including version directory.
        """
        base_path = f"{self.prefix}/{model_type}/{exp_name}"
        v1_path = f"{base_path}/v1"

        try:
            blobs = list(self.bucket.list_blobs(prefix=f"{v1_path}/", max_results=1))
            if blobs:
                return v1_path
        except Exception:
            pass

        return base_path

    def _load_enriched_experiment_metadata(
        self, model_type: str, exp_name: str
    ) -> dict[str, Any]:
        """Load enriched metadata for a single experiment.

        Args:
            model_type: The model type.
            exp_name: The experiment name.

        Returns:
            Dictionary with enriched experiment metadata.
        """
        base_path = self._get_experiment_version_path(model_type, exp_name)

        experiment: dict[str, Any] = {
            "full_name": exp_name,
            "experiment_name": exp_name,
            "model_type": model_type,
            "timestamp": "",
            "metrics": {},
            "parameters": {},
            "model_info": {},
        }

        # Load metadata.json
        try:
            blob = self.bucket.blob(f"{base_path}/metadata.json")
            content = blob.download_as_text()
            metadata = json.loads(content)
            for key, value in metadata.items():
                if key not in ["metrics", "parameters", "model_info"]:
                    experiment[key] = value
        except google.cloud.exceptions.NotFound:
            pass
        except Exception as e:
            logger.warning(f"Error loading metadata for {exp_name}: {e}")

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
        self, model_type: str, exp_name: str
    ) -> dict[str, Any]:
        """Load detailed experiment information including all files.

        Args:
            model_type: The model type.
            exp_name: The experiment name.

        Returns:
            Dictionary with detailed experiment information.
        """
        cache_key = f"details_{model_type}_{exp_name}"
        if cache_key in self._metadata_cache:
            return self._metadata_cache[cache_key]

        try:
            details: dict[str, Any] = {}
            base_path = self._get_experiment_version_path(model_type, exp_name)

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
        self, model_type: str, exp_name: str
    ) -> pd.DataFrame | None:
        """Load feature importance data for an experiment.

        Tries multiple formats: CSV, coefficients.csv, JSON.

        Args:
            model_type: The model type.
            exp_name: The experiment name.

        Returns:
            DataFrame with feature importance data or None if not found.
        """
        base_path = self._get_experiment_version_path(model_type, exp_name)

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
        self, model_type: str, exp_name: str, dataset: str = "test"
    ) -> pd.DataFrame | None:
        """Load predictions for an experiment.

        Args:
            model_type: The model type.
            exp_name: The experiment name.
            dataset: Dataset name ('train', 'tune', 'test').

        Returns:
            DataFrame with predictions or None if not found.
        """
        try:
            base_path = self._get_experiment_version_path(model_type, exp_name)
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
    """Get or create singleton ExperimentLoader instance.

    Args:
        bucket_name: Optional bucket name override.

    Returns:
        ExperimentLoader instance.
    """
    global _experiment_loader
    if _experiment_loader is None:
        _experiment_loader = ExperimentLoader(bucket_name)
    return _experiment_loader
