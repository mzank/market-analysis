"""
Configuration constants for the market_analysis project.

This module centralizes cache settings, schema versioning,
parallelization parameters, and storage configuration.

Cache Settings:

| Setting          | Default Value     | Description                                           |
| ---------------- | ----------------- | ----------------------------------------------------- |
| CACHE_DIR        | "cache_history"   | Directory where cached data is stored.                |
| CACHE_MAX_AGE    | 1                 | Maximum cache age in days before data is refreshed.   |
| SCHEMA_VERSION   | "1.0"             | Version of the cached data schema.                    |
| PARQUET_ENGINE   | "pyarrow"         | Engine used for storing Parquet files.                |
| MAX_WORKERS      | 6                 | Maximum number of parallel threads for fetching data. |
"""

from typing import Literal

CACHE_DIR = "cache_history"
CACHE_MAX_AGE = 1
SCHEMA_VERSION = "1.0"
PARQUET_ENGINE: Literal["auto", "pyarrow", "fastparquet"] = "pyarrow"
MAX_WORKERS = 6
