"""Sampling utilities for data visualization performance optimization."""

import logging
from typing import Optional, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def smart_sample_dataframe(
    df: pd.DataFrame,
    max_rows: int = 10000,
    threshold: int = 25000,
    random_state: int = 42,
    strategy: str = "random",
) -> Tuple[pd.DataFrame, bool]:
    """
    Intelligently sample a DataFrame for visualization performance.

    This function provides a standardized approach to sampling large datasets
    for visualization purposes, ensuring consistent behavior across all charts
    while maintaining data representativeness.

    Args:
        df: Input DataFrame to potentially sample
        max_rows: Maximum number of rows to return when sampling
        threshold: Minimum number of rows that triggers sampling
        random_state: Random seed for reproducible sampling
        strategy: Sampling strategy ('random', 'stratified', or 'top_rated')

    Returns:
        Tuple of (sampled_dataframe, was_sampled)
        - sampled_dataframe: The original or sampled DataFrame
        - was_sampled: Boolean indicating whether sampling was applied

    Examples:
        >>> df_sample, was_sampled = smart_sample_dataframe(large_df)
        >>> if was_sampled:
        ...     logger.info(f"Sampled {len(df_sample)} rows from {len(large_df)}")
    """
    if len(df) <= threshold:
        logger.debug(
            f"DataFrame has {len(df)} rows, below threshold of {threshold}. No sampling applied."
        )
        return df.copy(), False

    logger.info(
        f"DataFrame has {len(df)} rows, above threshold of {threshold}. Applying {strategy} sampling to {max_rows} rows."
    )

    # Set random seed for reproducibility
    np.random.seed(random_state)

    if strategy == "random":
        # Simple random sampling
        sampled_df = df.sample(n=max_rows, random_state=random_state)

    elif strategy == "stratified":
        # Stratified sampling by year (if year_published column exists)
        if "year_published" in df.columns:
            # Group by decade for stratified sampling
            df_with_decade = df.copy()
            df_with_decade["decade"] = (df_with_decade["year_published"] // 10) * 10

            # Calculate proportional sample sizes
            decade_counts = df_with_decade["decade"].value_counts()
            decade_proportions = decade_counts / len(df)

            sampled_dfs = []
            for decade, proportion in decade_proportions.items():
                decade_df = df_with_decade[df_with_decade["decade"] == decade]
                sample_size = max(1, int(proportion * max_rows))
                sample_size = min(sample_size, len(decade_df))

                if sample_size > 0:
                    decade_sample = decade_df.sample(n=sample_size, random_state=random_state)
                    sampled_dfs.append(decade_sample)

            sampled_df = pd.concat(sampled_dfs, ignore_index=True)
            # Drop the temporary decade column
            sampled_df = sampled_df.drop("decade", axis=1)

            # If we ended up with more than max_rows, randomly sample down
            if len(sampled_df) > max_rows:
                sampled_df = sampled_df.sample(n=max_rows, random_state=random_state)
        else:
            # Fall back to random sampling if no year_published column
            logger.warning(
                "Stratified sampling requested but no 'year_published' column found. Using random sampling."
            )
            sampled_df = df.sample(n=max_rows, random_state=random_state)

    elif strategy == "top_rated":
        # Sample top-rated games plus random selection
        if "bayes_average" in df.columns:
            # Take top 30% by rating, then random sample the rest
            top_portion = 0.3
            top_count = int(max_rows * top_portion)
            random_count = max_rows - top_count

            # Get top rated games
            top_games = df.nlargest(top_count, "bayes_average")

            # Get random sample from remaining games
            remaining_games = df.drop(top_games.index)
            if len(remaining_games) > 0:
                random_sample_size = min(random_count, len(remaining_games))
                random_games = remaining_games.sample(
                    n=random_sample_size, random_state=random_state
                )
                sampled_df = pd.concat([top_games, random_games], ignore_index=True)
            else:
                sampled_df = top_games
        else:
            # Fall back to random sampling if no bayes_average column
            logger.warning(
                "Top-rated sampling requested but no 'bayes_average' column found. Using random sampling."
            )
            sampled_df = df.sample(n=max_rows, random_state=random_state)

    else:
        raise ValueError(
            f"Unknown sampling strategy: {strategy}. Use 'random', 'stratified', or 'top_rated'."
        )

    logger.info(
        f"Sampled {len(sampled_df)} rows from original {len(df)} rows using {strategy} strategy."
    )
    return sampled_df, True


def add_jitter(df: pd.DataFrame, columns: dict, random_state: int = 42) -> pd.DataFrame:
    """
    Add jitter to specified columns to reduce overplotting in visualizations.

    Args:
        df: Input DataFrame
        columns: Dictionary mapping column names to jitter ranges
                Example: {'year_published': 0.3, 'average_weight': 0.05}
        random_state: Random seed for reproducible jitter

    Returns:
        DataFrame with jittered columns added (original columns preserved)

    Examples:
        >>> jitter_config = {'year_published': 0.3, 'average_weight': 0.05}
        >>> df_jittered = add_jitter(df, jitter_config)
        >>> # Creates 'year_published_jittered' and 'average_weight_jittered' columns
    """
    np.random.seed(random_state)
    df_result = df.copy()

    for column, jitter_range in columns.items():
        if column in df_result.columns:
            jitter_column = f"{column}_jittered"
            jitter_values = np.random.uniform(-jitter_range, jitter_range, len(df_result))
            df_result[jitter_column] = df_result[column] + jitter_values
            logger.debug(f"Added jitter to {column} with range ±{jitter_range}")
        else:
            logger.warning(f"Column {column} not found in DataFrame. Skipping jitter.")

    return df_result


def prepare_visualization_data(
    df: pd.DataFrame, sampling_config: Optional[dict] = None, jitter_config: Optional[dict] = None
) -> Tuple[pd.DataFrame, bool]:
    """
    Prepare data for visualization by applying sampling and jitter in one step.

    This is a convenience function that combines smart sampling and jitter
    application for common visualization preparation workflows.

    Args:
        df: Input DataFrame
        sampling_config: Configuration for sampling (passed to smart_sample_dataframe)
        jitter_config: Configuration for jitter (passed to add_jitter)

    Returns:
        Tuple of (prepared_dataframe, was_sampled)

    Examples:
        >>> sampling_config = {'max_rows': 8000, 'strategy': 'stratified'}
        >>> jitter_config = {'year_published': 0.3, 'average_rating': 0.05}
        >>> df_viz, was_sampled = prepare_visualization_data(df, sampling_config, jitter_config)
    """
    # Apply sampling if configured
    if sampling_config:
        df_result, was_sampled = smart_sample_dataframe(df, **sampling_config)
    else:
        df_result, was_sampled = df.copy(), False

    # Apply jitter if configured
    if jitter_config:
        df_result = add_jitter(df_result, jitter_config)

    return df_result, was_sampled
