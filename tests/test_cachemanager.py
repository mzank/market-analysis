"""
Unit tests for the CacheManager class.

This module contains pytest-based tests for the CacheManager,
verifying correct behavior for cache path construction, freshness
validation, schema version enforcement, and file I/O handling.

The tests cover:

- Proper generation of cache file paths.
- Freshness evaluation for recent, outdated, and empty datasets.
- Saving and loading of cached data with valid schema metadata.
- Rejection of cached data with mismatched schema versions.
- Graceful handling of missing or corrupted cache files.

Temporary directories are used to ensure filesystem isolation and to
avoid side effects between test runs.
"""

import os
from datetime import timedelta

import pandas as pd
import pytest

from market_analysis.cachemanager import CacheManager


@pytest.fixture
def cache_manager(tmp_path):
    """Provide CacheManager with isolated temporary directory."""
    return CacheManager(cache_dir=tmp_path, schema_version="test_schema")


@pytest.fixture
def sample_df():
    """Create a simple DataFrame with recent business-day index."""
    today = pd.Timestamp.now().normalize()
    index = pd.bdate_range(end=today, periods=5)
    df = pd.DataFrame({"Close": range(5)}, index=index)
    return df


def test_get_cache_path(cache_manager):
    ticker = "TEST"
    path = cache_manager.get_cache_path(ticker)

    assert str(path).endswith(os.path.join(cache_manager.cache_dir, "TEST.parquet"))


def test_is_fresh_with_recent_data(cache_manager, sample_df):
    assert cache_manager.is_fresh(sample_df) is True


def test_is_fresh_with_old_data(cache_manager):
    old_date = pd.Timestamp.now().normalize() - timedelta(days=365)
    index = pd.bdate_range(end=old_date, periods=5)
    df = pd.DataFrame({"Close": range(5)}, index=index)

    assert cache_manager.is_fresh(df) is False


def test_is_fresh_empty_dataframe(cache_manager):
    df = pd.DataFrame()
    assert cache_manager.is_fresh(df) is False


def test_save_and_load_valid_schema(cache_manager, sample_df):
    ticker = "VALID"

    cache_manager.save(sample_df, ticker)
    loaded = cache_manager.load(ticker)

    assert loaded is not None
    assert loaded.equals(sample_df)
    assert loaded.attrs.get("schema_version") == "test_schema"


def test_load_returns_none_for_wrong_schema(cache_manager, sample_df):
    ticker = "WRONG_SCHEMA"

    # Save with different schema version
    df = sample_df.copy()
    df.attrs["schema_version"] = "other_schema"
    path = cache_manager.get_cache_path(ticker)
    df.to_parquet(path)

    loaded = cache_manager.load(ticker)

    assert loaded is None


def test_load_returns_none_if_file_missing(cache_manager):
    assert cache_manager.load("DOES_NOT_EXIST") is None


def test_load_handles_corrupted_file(cache_manager):
    ticker = "CORRUPTED"
    path = cache_manager.get_cache_path(ticker)

    # Create invalid parquet file
    with open(path, "w") as f:
        f.write("not a parquet file")

    loaded = cache_manager.load(ticker)

    assert loaded is None
