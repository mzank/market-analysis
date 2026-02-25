"""
Unit tests for the Asset class in the market_analysis.asset module.

This module uses pytest to validate the behavior of the Asset class, including:

- Fetching historical price data from yfinance or cache.
- Handling edge cases such as empty data, missing price columns, and timezones.
- Computing and printing summary statistics (total return, CAGR, volatility, drawdown, autocorrelation).
- Generating plots of price, cumulative return, drawdown, rolling volatility, and Sharpe ratio.

Fixtures:
- sample_prices: provides a simple price series DataFrame for testing.
- mock_cache_manager: mocks the caching behavior for Asset instances.

Tests cover:
- fetch() from cache and yfinance, including edge cases
- print_asset_stats() with normal and insufficient data
- plot_asset_stats() for display, saving, log-scale, and insufficient data
"""

import zoneinfo
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest

from market_analysis.asset import Asset

# --- Fixtures ---


@pytest.fixture
def sample_prices():
    """Simple price series for testing"""
    dates = pd.date_range("2020-01-01", periods=5, freq="D")
    prices = pd.Series([100, 105, 102, 108, 110], index=dates)
    df = pd.DataFrame({"AdjClose": prices})
    return df


@pytest.fixture
def mock_cache_manager(sample_prices):
    """Mock cache manager"""
    cm = Mock()
    cm.load.return_value = None
    cm.is_fresh.return_value = True
    cm.save.return_value = None
    return cm


# --- Tests for fetch() ---


def test_asset_fetch_from_yfinance(monkeypatch, mock_cache_manager, sample_prices):
    mock_ticker = Mock()
    mock_hist = sample_prices.copy()
    mock_hist.columns = ["Adj Close"]
    mock_ticker.history.return_value = mock_hist
    monkeypatch.setattr("market_analysis.asset.yf.Ticker", lambda ticker: mock_ticker)

    asset = Asset("TEST", "Test Asset", mock_cache_manager)
    df = asset.fetch()
    assert df is not None
    assert "AdjClose" in df.columns
    assert df.shape == (5, 1)
    mock_cache_manager.save.assert_called_once_with(df, "TEST")


def test_asset_fetch_from_cache(mock_cache_manager, sample_prices):
    mock_cache_manager.load.return_value = sample_prices
    mock_cache_manager.is_fresh.return_value = True

    asset = Asset("TEST", "Test Asset", mock_cache_manager)
    df = asset.fetch()
    assert df.equals(sample_prices)
    mock_cache_manager.save.assert_not_called()


# --- Edge cases for fetch() ---


def test_fetch_empty_dataframe(monkeypatch, mock_cache_manager):
    mock_ticker = Mock()
    mock_ticker.history.return_value = pd.DataFrame()
    monkeypatch.setattr("market_analysis.asset.yf.Ticker", lambda ticker: mock_ticker)

    asset = Asset("TEST", "Test Asset", mock_cache_manager)
    result = asset.fetch()
    assert result is None


def test_fetch_no_price_columns(monkeypatch, mock_cache_manager):
    df = pd.DataFrame({"Open": [1, 2, 3], "High": [1, 2, 3]})
    mock_ticker = Mock()
    mock_ticker.history.return_value = df
    monkeypatch.setattr("market_analysis.asset.yf.Ticker", lambda ticker: mock_ticker)

    asset = Asset("TEST", "Test Asset", mock_cache_manager)
    result = asset.fetch()
    assert result is None


def test_fetch_with_timezone(monkeypatch, mock_cache_manager):
    # Use a UTC+2 offset tz instead of US/Eastern
    tz = zoneinfo.ZoneInfo("Etc/GMT-2")
    dates = pd.date_range("2020-01-01", periods=3, freq="D", tz=tz)
    df = pd.DataFrame({"Adj Close": [100, 105, 110]}, index=dates)

    mock_ticker = Mock()
    mock_ticker.history.return_value = df
    monkeypatch.setattr("market_analysis.asset.yf.Ticker", lambda ticker: mock_ticker)

    asset = Asset("TEST", "Test Asset", mock_cache_manager)
    result = asset.fetch()
    assert result.index.tz is None


def test_fetch_with_close_column(monkeypatch, mock_cache_manager):
    df = pd.DataFrame(
        {"Close": [100, 101, 102]},
        index=pd.date_range("2020-01-01", periods=3, freq="D"),
    )

    mock_ticker = Mock()
    mock_ticker.history.return_value = df
    monkeypatch.setattr("market_analysis.asset.yf.Ticker", lambda ticker: mock_ticker)

    asset = Asset("TEST", "Test Asset", mock_cache_manager)
    result = asset.fetch()

    assert result is not None
    assert "AdjClose" in result.columns


# --- Tests for print_asset_stats() ---


def test_print_asset_stats(capsys, sample_prices, mock_cache_manager):
    asset = Asset("TEST", "Test Asset", mock_cache_manager)
    asset.df = sample_prices

    asset.print_asset_stats(start_date="2020-01-01", end_date="2020-01-05")
    captured = capsys.readouterr()
    assert "Asset statistics: Test Asset" in captured.out
    assert "Total return" in captured.out
    assert "CAGR" in captured.out
    assert "Max drawdown" in captured.out


def test_print_asset_stats_insufficient(capsys, mock_cache_manager):
    asset = Asset("TEST", "Test Asset", mock_cache_manager)
    asset.df = pd.DataFrame({"AdjClose": [100]}, index=pd.to_datetime(["2020-01-01"]))

    asset.print_asset_stats(start_date="2020-01-01", end_date="2020-01-01")
    captured = capsys.readouterr()
    assert "insufficient data" in captured.out


def test_print_asset_stats_non_daily_frequency(
    capsys, sample_prices, mock_cache_manager
):
    asset = Asset("TEST", "Test Asset", mock_cache_manager)
    asset.df = sample_prices

    asset.print_asset_stats(
        start_date="2020-01-01",
        end_date="2020-01-05",
        frequency="ME",
    )

    captured = capsys.readouterr()
    assert "Frequency: ME" in captured.out


# --- Tests for plot_asset_stats() ---


def test_plot_asset_stats_no_crash(monkeypatch, sample_prices, mock_cache_manager):
    asset = Asset("TEST", "Test Asset", mock_cache_manager)
    asset.df = sample_prices
    monkeypatch.setattr("matplotlib.pyplot.show", lambda: None)
    asset.plot_asset_stats(start_date="2020-01-01", end_date="2020-01-05")


def test_plot_asset_stats_save(
    monkeypatch, tmp_path, sample_prices, mock_cache_manager
):
    asset = Asset("TEST", "Test Asset", mock_cache_manager)
    asset.df = sample_prices

    monkeypatch.setattr("matplotlib.pyplot.show", lambda: None)
    # Patch safe_filename to preserve tmp_path
    monkeypatch.setattr("market_analysis.asset.safe_filename", lambda x: x)

    save_path = tmp_path / "plot.png"
    asset.plot_asset_stats(
        start_date="2020-01-01", end_date="2020-01-05", save_path=str(save_path)
    )
    assert save_path.exists()


def test_plot_asset_stats_insufficient(monkeypatch, mock_cache_manager):
    asset = Asset("TEST", "Test Asset", mock_cache_manager)
    asset.df = pd.DataFrame({"AdjClose": [100]}, index=pd.to_datetime(["2020-01-01"]))

    monkeypatch.setattr("matplotlib.pyplot.show", lambda: None)
    asset.plot_asset_stats(start_date="2020-01-01", end_date="2020-01-01")


def test_plot_asset_stats_log(monkeypatch, sample_prices, mock_cache_manager):
    """Test log_price branch"""
    asset = Asset("TEST", "Test Asset", mock_cache_manager)
    asset.df = sample_prices

    monkeypatch.setattr("matplotlib.pyplot.show", lambda: None)
    asset.plot_asset_stats(
        start_date="2020-01-01", end_date="2020-01-05", log_price=True
    )


def test_plot_asset_stats_non_daily_frequency(
    monkeypatch, sample_prices, mock_cache_manager
):
    asset = Asset("TEST", "Test Asset", mock_cache_manager)
    asset.df = sample_prices

    monkeypatch.setattr("matplotlib.pyplot.show", lambda: None)

    asset.plot_asset_stats(
        start_date="2020-01-01",
        end_date="2020-01-05",
        frequency="ME",
    )
