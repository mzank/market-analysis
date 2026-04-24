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
    configuration mapping and retrieves their historical
    data using a ThreadPoolExecutor.
    """

    def __init__(
        self, ticker_config: dict[str, dict[str, str]], max_workers: int = MAX_WORKERS
    ) -> None:
        """
        Initialize the DataFetcher.

        Parameters
        ----------
        ticker_config : dict[str, dict[str, str]]
            Mapping of ticker symbols to configuration dictionaries.
            Each configuration must include a "label" key
            (e.g., {"^ATX": {"label": "ATX"}}).
        max_workers : int, optional
            Maximum number of threads used for concurrent downloads.
        """

        self.ticker_config = ticker_config
        self.max_workers = max_workers
        self.cache_manager = CacheManager()

    def load_assets(self) -> dict[str, Asset]:
        """
        Create Asset instances and fetch their data concurrently.

        Assets are created in the order defined by ``ticker_config``.
        Only assets whose data was successfully fetched are included
        in the result.

        Returns
        -------
        dict[str, Asset]
            Mapping of ticker symbols to Asset instances with
            successfully loaded data.
        """

        # Create assets in ticker_config order
        assets = [
            Asset(ticker, cfg["label"], self.cache_manager)
            for ticker, cfg in self.ticker_config.items()
        ]

        assets_by_ticker = {asset.ticker: asset for asset in assets}

        # Fetch concurrently
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {asset.ticker: executor.submit(asset.fetch) for asset in assets}

        # Assemble results in ticker_config order
        results: dict[str, Asset] = {}
        for ticker in self.ticker_config:
            future = futures.get(ticker)
            if future is None:
                continue
            df = future.result()
            if df is not None:
                results[ticker] = assets_by_ticker[ticker]

        return results
