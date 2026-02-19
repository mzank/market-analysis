"""
Concurrent asset loading utilities.

This module defines the DataFetcher class, which creates Asset
instances and downloads their data in parallel using threads.
"""

from concurrent.futures import ThreadPoolExecutor

from .asset import Asset
from .cachemanager import CacheManager
from .config import MAX_WORKERS


class DataFetcher:
    """
    Load and manage multiple Asset objects concurrently.

    DataFetcher initializes Asset instances from a ticker
    configuration dictionary and retrieves their historical
    data using a ThreadPoolExecutor.
    """

    def __init__(self, ticker_config, max_workers=MAX_WORKERS):
        """
        Initialize the DataFetcher.

        Parameters
        ----------
        ticker_config : dict
            Dictionary mapping tickers to configuration dictionaries
            (e.g., {"^ATX": {"label": "ATX"}}).
        max_workers : int
            Maximum number of threads used for concurrent downloads.
        """

        self.ticker_config = ticker_config
        self.max_workers = max_workers
        self.cache_manager = CacheManager()

    def load_assets(self):
        """
        Create Asset instances and fetch their data concurrently.

        Assets are returned in the same order as defined in the
        ticker configuration.

        Returns
        -------
        dict
            Dictionary mapping ticker symbols to Asset instances
            with successfully loaded data.
        """

        # Create assets in ticker_config order
        assets = [
            Asset(ticker, cfg["label"], self.cache_manager)
            for ticker, cfg in self.ticker_config.items()
        ]

        # Fetch concurrently
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {asset.ticker: executor.submit(asset.fetch) for asset in assets}

        # Assemble results in ticker_config order
        results = {}
        for ticker in self.ticker_config.keys():
            future = futures.get(ticker)
            if future is None:
                continue
            df = future.result()
            if df is not None:
                # find the matching asset
                asset = next(a for a in assets if a.ticker == ticker)
                results[ticker] = asset

        return results
