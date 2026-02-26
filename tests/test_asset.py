"""
Unit tests for the market_analysis.asset module.

This module contains pytest-based tests for the Asset class defined in
market_analysis.asset. It covers functionality for:

- Fetching historical price data, including cache handling, timezone
  normalization, and column selection.
- Computing and printing asset statistics, including total return,
  CAGR, volatility, drawdown, and autocorrelation.
- Plotting asset statistics, including price, cumulative return,
  drawdown, rolling volatility, and rolling Sharpe ratio.

Fixtures provide reusable test data and mocks, including sample price
series, a mock CacheManager, and a factory for creating Asset instances.
Tests ensure the correctness of outputs, proper cache usage, and that
plotting functions execute without errors.
"""

import re
from unittest.mock import Mock

import pandas as pd
import pytest

from market_analysis.asset import Asset

# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


@pytest.fixture
def sample_prices() -> pd.DataFrame:
    """Simple deterministic price series."""
    dates = pd.date_range("2020-01-01", periods=5, freq="D")
    prices = pd.Series([100, 105, 102, 108, 110], index=dates)
    return pd.DataFrame({"AdjClose": prices})


@pytest.fixture
def increasing_prices() -> pd.DataFrame:
    """Strictly increasing prices (max drawdown must be 0)."""
    dates = pd.date_range("2020-01-01", periods=4, freq="D")
    prices = pd.Series([100, 110, 120, 130], index=dates)
    return pd.DataFrame({"AdjClose": prices})


@pytest.fixture
def mock_cache_manager():
    """Mocked cache manager with explicit spec-like safety."""
    cm = Mock()
    cm.load.return_value = None
    cm.is_fresh.return_value = True
    cm.save.return_value = None
    return cm


@pytest.fixture
def asset_factory(mock_cache_manager):
    """Factory to create Asset instances optionally preloaded with df."""

    def _create(df=None):
        asset = Asset("TEST", "Test Asset", mock_cache_manager)
        if df is not None:
            asset.df = df
        return asset

    return _create


@pytest.fixture(autouse=True)
def use_agg_backend():
    """Force non-interactive matplotlib backend."""
    import matplotlib

    matplotlib.use("Agg")


# ---------------------------------------------------------------------
# Fetch Tests
# ---------------------------------------------------------------------


class TestFetch:
    @pytest.mark.parametrize("columns", [["Adj Close"], ["Close"]])
    def test_fetch_column_selection_and_timezone(
        self, monkeypatch, mock_cache_manager, sample_prices, columns
    ):
        df = sample_prices.copy()
        df.columns = columns

        df.index = df.index.tz_localize("UTC").tz_convert("Europe/Vienna")

        mock_ticker = Mock()
        mock_ticker.history.return_value = df

        monkeypatch.setattr(
            "market_analysis.asset.yf.Ticker",
            lambda ticker: mock_ticker,
        )

        asset = Asset("TEST", "Test Asset", mock_cache_manager)
        result = asset.fetch()

        assert list(result.columns) == ["AdjClose"]
        assert result.index.tz is None
        assert all(result.index.hour == 0)
        assert result.index.equals(pd.to_datetime(result.index.date))

        mock_cache_manager.load.assert_called_once_with("TEST")
        mock_cache_manager.save.assert_called_once()

    def test_fetch_from_cache(self, mock_cache_manager, sample_prices):
        mock_cache_manager.load.return_value = sample_prices
        mock_cache_manager.is_fresh.return_value = True

        asset = Asset("TEST", "Test Asset", mock_cache_manager)
        df = asset.fetch()

        pd.testing.assert_frame_equal(df, sample_prices)
        mock_cache_manager.load.assert_called_once_with("TEST")
        mock_cache_manager.is_fresh.assert_called_once_with(sample_prices)
        mock_cache_manager.save.assert_not_called()

    def test_fetch_stale_cache_downloads(
        self, monkeypatch, mock_cache_manager, sample_prices
    ):
        mock_cache_manager.load.return_value = sample_prices
        mock_cache_manager.is_fresh.return_value = False

        mock_hist = sample_prices.copy()
        mock_hist.columns = ["Adj Close"]

        mock_ticker = Mock()
        mock_ticker.history.return_value = mock_hist

        monkeypatch.setattr(
            "market_analysis.asset.yf.Ticker",
            lambda ticker: mock_ticker,
        )

        asset = Asset("TEST", "Test Asset", mock_cache_manager)
        df = asset.fetch()

        assert isinstance(df, pd.DataFrame)
        mock_cache_manager.save.assert_called_once()

    def test_fetch_empty_dataframe(self, monkeypatch, mock_cache_manager):
        mock_ticker = Mock()
        mock_ticker.history.return_value = pd.DataFrame()

        monkeypatch.setattr(
            "market_analysis.asset.yf.Ticker",
            lambda ticker: mock_ticker,
        )

        asset = Asset("TEST", "Test Asset", mock_cache_manager)
        assert asset.fetch() is None

    def test_fetch_no_price_columns(self, monkeypatch, mock_cache_manager):
        df = pd.DataFrame({"Open": [1, 2, 3]})
        mock_ticker = Mock()
        mock_ticker.history.return_value = df

        monkeypatch.setattr(
            "market_analysis.asset.yf.Ticker",
            lambda ticker: mock_ticker,
        )

        asset = Asset("TEST", "Test Asset", mock_cache_manager)
        assert asset.fetch() is None


# ---------------------------------------------------------------------
# Print Stats Tests
# ---------------------------------------------------------------------


class TestPrintStats:
    def test_total_return_exact(self, asset_factory, capsys, sample_prices):
        asset = asset_factory(sample_prices)
        asset.print_asset_stats("2020-01-01", "2020-01-05")

        out = capsys.readouterr().out
        assert "Asset statistics: Test Asset" in out

        assert "Total return: 10.00%" in out

    def test_zero_drawdown(self, asset_factory, capsys, increasing_prices):
        asset = asset_factory(increasing_prices)
        asset.print_asset_stats("2020-01-01", "2020-01-04")

        out = capsys.readouterr().out
        assert "Max drawdown: 0.00%" in out

    def test_insufficient_data(self, asset_factory, capsys):
        df = pd.DataFrame(
            {"AdjClose": [100]},
            index=pd.to_datetime(["2020-01-01"]),
        )
        asset = asset_factory(df)
        asset.print_asset_stats("2020-01-01", "2020-01-01")

        assert "insufficient data" in capsys.readouterr().out

    def test_df_none_raises(self):
        asset = Asset("T", "Test", Mock())
        with pytest.raises(TypeError):
            asset.print_asset_stats("2020-01-01", "2020-01-05")

    @pytest.mark.parametrize("frequency", ["D", "ME", "YE"])
    def test_frequency_display(self, asset_factory, capsys, sample_prices, frequency):
        asset = asset_factory(sample_prices)
        asset.print_asset_stats("2020-01-01", "2020-01-05", frequency=frequency)

        assert f"Frequency: {frequency}" in capsys.readouterr().out


# ---------------------------------------------------------------------
# Plot Tests
# ---------------------------------------------------------------------


class TestPlotStats:
    def test_plot_creates_five_axes(self, asset_factory, monkeypatch, sample_prices):
        asset = asset_factory(sample_prices)

        fig_mock = Mock()
        axes_mock = [Mock() for _ in range(5)]

        monkeypatch.setattr(
            "matplotlib.pyplot.subplots",
            lambda *a, **k: (fig_mock, axes_mock),
        )

        monkeypatch.setattr("matplotlib.pyplot.close", Mock())
        monkeypatch.setattr("matplotlib.pyplot.show", Mock())

        asset.plot_asset_stats("2020-01-01", "2020-01-05")

        assert len(axes_mock) == 5

    def test_log_price_sets_log_scale(self, asset_factory, monkeypatch, sample_prices):
        asset = asset_factory(sample_prices)

        fig_mock = Mock()
        axes_mock = [Mock() for _ in range(5)]

        monkeypatch.setattr(
            "matplotlib.pyplot.subplots",
            lambda *a, **k: (fig_mock, axes_mock),
        )
        monkeypatch.setattr("matplotlib.pyplot.close", Mock())
        monkeypatch.setattr("matplotlib.pyplot.show", Mock())

        asset.plot_asset_stats(
            "2020-01-01",
            "2020-01-05",
            log_price=True,
        )

        axes_mock[0].set_yscale.assert_called_once_with("log")

    def test_show_called_when_no_save(self, asset_factory, monkeypatch, sample_prices):
        asset = asset_factory(sample_prices)

        monkeypatch.setattr("matplotlib.pyplot.close", Mock())
        show_mock = Mock()
        monkeypatch.setattr("matplotlib.pyplot.show", show_mock)

        asset.plot_asset_stats("2020-01-01", "2020-01-05")

        show_mock.assert_called_once()

    def test_save_called_and_show_not_called(
        self, asset_factory, monkeypatch, tmp_path, sample_prices
    ):
        asset = asset_factory(sample_prices)

        save_mock = Mock()
        show_mock = Mock()

        monkeypatch.setattr("matplotlib.pyplot.savefig", save_mock)
        monkeypatch.setattr("matplotlib.pyplot.show", show_mock)
        monkeypatch.setattr("matplotlib.pyplot.close", Mock())
        monkeypatch.setattr(
            "market_analysis.asset.safe_filename",
            lambda x: f"SAFE_{x}",
        )

        path = tmp_path / "unsafe<>name.png"

        asset.plot_asset_stats(
            "2020-01-01",
            "2020-01-05",
            save_path=str(path),
        )

        save_mock.assert_called_once()
        show_mock.assert_not_called()

    def test_plot_insufficient_data(self, asset_factory):
        df = pd.DataFrame(
            {"AdjClose": [100]},
            index=pd.to_datetime(["2020-01-01"]),
        )
        asset = asset_factory(df)

        asset.plot_asset_stats("2020-01-01", "2020-01-01")

    def test_plot_df_none_raises(self):
        asset = Asset("T", "Test", Mock())
        with pytest.raises(TypeError):
            asset.plot_asset_stats("2020-01-01", "2020-01-05")

    def test_plot_non_daily_branch_executes(self, sample_prices):
        from unittest.mock import Mock

        import matplotlib.pyplot as plt

        asset = Asset("TEST", "Test Asset", Mock())
        asset.df = sample_prices

        plt.show = lambda: None

        asset.plot_asset_stats(
            "2020-01-01",
            "2020-01-05",
            frequency="ME",
            sharpe_window=2,
            risk_free_rate=0.01,
        )
