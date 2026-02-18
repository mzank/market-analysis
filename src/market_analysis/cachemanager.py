"""
Caching utilities for storing and retrieving historical market data.

This module defines the CacheManager class, which stores price data
locally in Parquet format and validates cache freshness and schema
versioning.
"""

import os

import pandas as pd

from .config import CACHE_DIR, CACHE_MAX_AGE, PARQUET_ENGINE, SCHEMA_VERSION


class CacheManager:
    """
    Manage local caching of historical price data.

    The CacheManager handles reading, writing, validating freshness,
    and maintaining schema version consistency for cached datasets.
    """

    def __init__(self, cache_dir=CACHE_DIR, schema_version=SCHEMA_VERSION):
        """
        Initialize the CacheManager.

        Parameters
        ----------
        cache_dir : str
            Directory where cached files are stored.
        schema_version : str
            Version string used to validate cached file compatibility.
        """

        self.cache_dir = cache_dir
        self.schema_version = schema_version
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_cache_path(self, ticker):
        """
        Return the full cache file path for a ticker.

        Parameters
        ----------
        ticker : str
            Asset ticker symbol.

        Returns
        -------
        str
            Absolute path to the corresponding Parquet file.
        """

        return os.path.join(self.cache_dir, f"{ticker}.parquet")

    def is_fresh(self, df):
        """
        Determine whether cached data is sufficiently recent.

        Freshness is determined by comparing the most recent date
        in the dataset to the latest business day.

        Parameters
        ----------
        df : pandas.DataFrame
            Cached price data.

        Returns
        -------
        bool
            True if data is fresh, otherwise False.
        """

        if df.empty:
            return False

        youngest_date = df.index.max().normalize()
        ref_day = pd.offsets.BDay().rollback(pd.Timestamp.now().normalize())

        age = (ref_day - youngest_date).days
        return age <= CACHE_MAX_AGE

    def load(self, ticker):
        """
        Load cached data for a ticker if available and valid.

        Parameters
        ----------
        ticker : str
            Asset ticker symbol.

        Returns
        -------
        pandas.DataFrame or None
            Cached DataFrame if valid, otherwise None.
        """

        path = self.get_cache_path(ticker)
        if os.path.exists(path):
            try:
                df = pd.read_parquet(path, engine=PARQUET_ENGINE)
                if df.attrs.get("schema_version") == self.schema_version:
                    return df
            except Exception:
                print(f"Cache corrupted for {ticker}, refetching.")
        return None

    def save(self, df, ticker):
        """
        Save price data to the cache.

        Parameters
        ----------
        df : pandas.DataFrame
            Price data to store.
        ticker : str
            Asset ticker symbol.

        Returns
        -------
        None
        """

        df.attrs["schema_version"] = self.schema_version
        path = self.get_cache_path(ticker)
        df.to_parquet(path, engine=PARQUET_ENGINE)
