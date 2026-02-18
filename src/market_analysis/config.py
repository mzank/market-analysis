"""
Configuration constants for the market_analysis project.

This module centralizes cache settings, schema versioning,
parallelization parameters, and storage configuration.
"""

CACHE_DIR = "cache_history"
CACHE_MAX_AGE = 0
SCHEMA_VERSION = "1.0"
PARQUET_ENGINE = "pyarrow"
MAX_WORKERS = 6
