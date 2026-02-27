"""
Tests for the market_analysis CLI module.

This module verifies that the command-line interface correctly parses
arguments, initializes the DataFetcher, loads assets, and invokes
the expected asset methods with proper parameters. External
dependencies are mocked to avoid network access and filesystem I/O.
"""

import sys
from unittest.mock import MagicMock

import pytest

from market_analysis import cli


@pytest.fixture
def mock_datafetcher(monkeypatch):
    """
    Provide a mocked DataFetcher and asset instance.

    Returns
    -------
    tuple
        Mocked DataFetcher class, instance, and asset object.
    """

    # Create mock asset
    mock_asset = MagicMock()
    mock_asset.label = "TEST"

    # Load_assets returns dict of assets
    mock_fetcher_instance = MagicMock()
    mock_fetcher_instance.load_assets.return_value = {"TEST": mock_asset}

    mock_fetcher_class = MagicMock(return_value=mock_fetcher_instance)

    # Patch DataFetcher in cli module
    monkeypatch.setattr(cli, "DataFetcher", mock_fetcher_class)

    return mock_fetcher_class, mock_fetcher_instance, mock_asset


def test_cli_execution_with_required_arguments(monkeypatch, mock_datafetcher):
    """
    Verify CLI execution with required arguments.

    Ensures DataFetcher is initialized correctly and asset methods
    are called with expected parameters.
    """

    mock_fetcher_class, mock_fetcher_instance, mock_asset = mock_datafetcher

    test_args = [
        "market-analysis",
        "--tickers",
        "TEST",
        "--start",
        "2020-01-01",
        "--end",
        "2021-01-01",
    ]

    monkeypatch.setattr(sys, "argv", test_args)

    cli.main()

    # Verify DataFetcher initialized correctly
    mock_fetcher_class.assert_called_once_with({"TEST": {"label": "TEST"}})

    # Verify assets loaded
    mock_fetcher_instance.load_assets.assert_called_once()

    # Verify stats printed correctly
    mock_asset.print_asset_stats.assert_called_once_with(
        "2020-01-01",
        "2021-01-01",
        frequency="ME",
    )

    # Verify plotting called correctly
    mock_asset.plot_asset_stats.assert_called_once_with(
        start_date="2020-01-01",
        end_date="2021-01-01",
        log_price=True,
        sharpe_window=126,
        risk_free_rate=0.02,
        save_path="Stats_TEST.pdf",
    )


def test_cli_default_end_date(monkeypatch, mock_datafetcher):
    """
    Verify CLI uses default end date when not explicitly provided.
    """

    mock_fetcher_class, mock_fetcher_instance, mock_asset = mock_datafetcher

    test_args = [
        "market-analysis",
        "--tickers",
        "TEST",
        "--start",
        "2020-01-01",
    ]

    monkeypatch.setattr(sys, "argv", test_args)

    cli.main()

    # Ensure print called once
    assert mock_asset.print_asset_stats.call_count == 1

    # Extract actual end date passed
    _, kwargs = mock_asset.plot_asset_stats.call_args

    assert kwargs["start_date"] == "2020-01-01"
    assert "end_date" in kwargs
    assert kwargs["log_price"] is True
    assert kwargs["sharpe_window"] == 126
    assert kwargs["risk_free_rate"] == 0.02


def test_cli_requires_tickers(monkeypatch):
    """
    Verify CLI exits when required arguments are missing.
    """

    test_args = [
        "market-analysis",
        "--start",
        "2020-01-01",
    ]

    monkeypatch.setattr(sys, "argv", test_args)

    with pytest.raises(SystemExit):
        cli.main()
