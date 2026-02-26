"""
Unit tests for the DataFetcher class in the datafetcher module.

These tests verify the behavior of DataFetcher, including:

- Successful concurrent loading of multiple Asset instances.
- Handling of partial failures where some assets return None.
- Proper passing of the max_workers parameter to ThreadPoolExecutor.
- Behavior when provided an empty ticker configuration.

The tests use pytest fixtures and unittest.mock to isolate DataFetcher
from external dependencies such as Asset, CacheManager, and threading.
"""

from unittest.mock import MagicMock, patch

import pytest

from market_analysis.datafetcher import DataFetcher


@pytest.fixture
def ticker_config():
    return {
        "AAA": {"label": "Asset A"},
        "BBB": {"label": "Asset B"},
        "CCC": {"label": "Asset C"},
    }


def test_load_assets_successful_fetches(ticker_config):
    """All assets return data and should be included in results."""

    with (
        patch("market_analysis.datafetcher.Asset") as MockAsset,
        patch("market_analysis.datafetcher.CacheManager"),
        patch("market_analysis.datafetcher.ThreadPoolExecutor") as MockExecutor,
    ):

        # mock Asset instances
        mock_assets = []
        for ticker in ticker_config:
            asset_instance = MagicMock()
            asset_instance.ticker = ticker
            asset_instance.fetch.return_value = "dataframe"
            mock_assets.append(asset_instance)

        # Asset() outputs the mocks one after the other
        MockAsset.side_effect = mock_assets

        # mock ThreadPoolExecutor
        mock_executor = MagicMock()
        MockExecutor.return_value.__enter__.return_value = mock_executor

        # futures for submit(): each future.result() yields "dataframe"
        mock_futures = [MagicMock(result=lambda: "dataframe") for _ in ticker_config]
        mock_executor.submit.side_effect = mock_futures

        # DataFetcher run
        fetcher = DataFetcher(ticker_config, max_workers=2)
        result = fetcher.load_assets()

        # assertions
        for key in result:
            assert result[key] is mock_assets[list(ticker_config).index(key)]
        assert len(result) == 3
        assert mock_executor.submit.call_count == 3


def test_load_assets_partial_failure(ticker_config):
    """Assets returning None should not appear in results."""

    with (
        patch("market_analysis.datafetcher.Asset") as MockAsset,
        patch("market_analysis.datafetcher.CacheManager"),
        patch("market_analysis.datafetcher.ThreadPoolExecutor") as MockExecutor,
    ):

        mock_assets = []
        for i, ticker in enumerate(ticker_config):
            asset_instance = MagicMock()
            asset_instance.ticker = ticker
            # First two succeed, last fails
            asset_instance.fetch.return_value = "dataframe" if i < 2 else None
            mock_assets.append(asset_instance)

        MockAsset.side_effect = mock_assets

        mock_executor = MagicMock()
        MockExecutor.return_value.__enter__.return_value = mock_executor

        mock_futures = [
            MagicMock(result=lambda i=i: "dataframe" if i < 2 else None)
            for i in range(len(ticker_config))
        ]
        mock_executor.submit.side_effect = mock_futures

        fetcher = DataFetcher(ticker_config)
        result = fetcher.load_assets()

        assert list(result.keys()) == ["AAA", "BBB"]
        assert "CCC" not in result
        assert len(result) == 2


def test_max_workers_passed_to_executor(ticker_config):
    """Ensure max_workers is passed to ThreadPoolExecutor."""

    with (
        patch("market_analysis.datafetcher.Asset"),
        patch("market_analysis.datafetcher.CacheManager"),
        patch("market_analysis.datafetcher.ThreadPoolExecutor") as MockExecutor,
    ):

        mock_executor = MagicMock()
        MockExecutor.return_value.__enter__.return_value = mock_executor

        mock_future = MagicMock()
        mock_future.result.return_value = None
        mock_executor.submit.return_value = mock_future

        fetcher = DataFetcher(ticker_config, max_workers=5)
        fetcher.load_assets()

        MockExecutor.assert_called_once_with(max_workers=5)


def test_empty_ticker_config():
    """Empty ticker config should return empty dict."""

    with (
        patch("market_analysis.datafetcher.Asset"),
        patch("market_analysis.datafetcher.CacheManager"),
        patch("market_analysis.datafetcher.ThreadPoolExecutor"),
    ):

        fetcher = DataFetcher({})
        result = fetcher.load_assets()

        assert result == {}
