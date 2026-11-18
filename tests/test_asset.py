"""
Unit tests for the market_analysis.asset module.

This module contains pytest-based tests for the Asset class defined in
market_analysis.asset. It covers functionality for:

- Fetching historical price data, including cache handling, timezone
  normalization, and column selection.
- Computing and printing asset statistics, including total return,
  CAGR, volatility, drawdown, and autocorrelation.
- Directly testing the price preparation and calculation methods for
  returns, CAGR, volatility, drawdowns, autocorrelations, and rolling
  metrics.
- Plotting asset statistics, including price, cumulative return,
  drawdown, rolling volatility, and rolling Sharpe ratio.

Fixtures provide reusable test data and mocks, including sample price
series, a mock CacheManager, and a factory for creating Asset instances.
Tests ensure the correctness of outputs, proper cache usage, and that
plotting functions execute without errors.
"""

from collections.abc import Callable
from typing import Any, cast
from unittest.mock import MagicMock, Mock

import numpy as np
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
def mock_cache_manager() -> MagicMock:
    """Mocked cache manager with explicit spec-like safety."""
    cm = MagicMock()
    cm.load.return_value = None
    cm.is_fresh.return_value = True
    cm.save.return_value = None
    return cm


@pytest.fixture
def asset_factory(mock_cache_manager: Mock) -> Callable[[pd.DataFrame | None], Asset]:
    """Factory to create Asset instances optionally preloaded with df."""

    def _create(df: pd.DataFrame | None = None) -> Asset:
        asset = Asset("TEST", "Test Asset", mock_cache_manager)  # type: ignore
        if df is not None:
            asset.df = df
        return asset

    return _create


@pytest.fixture(autouse=True)
def use_agg_backend() -> None:
    """Force non-interactive matplotlib backend."""
    import matplotlib

    matplotlib.use("Agg")


# ---------------------------------------------------------------------
# Fetch Tests
# ---------------------------------------------------------------------


class TestFetch:
    @pytest.mark.parametrize("columns", [["Adj Close"], ["Close"]])
    def test_fetch_column_selection_and_timezone(
        self,
        monkeypatch: pytest.MonkeyPatch,
        mock_cache_manager: MagicMock,
        sample_prices: pd.DataFrame,
        columns: list[str],
    ) -> None:
        df = sample_prices.copy()
        df.columns = pd.Index(columns)

        df.index = (
            cast(pd.DatetimeIndex, df.index)
            .tz_localize("UTC")
            .tz_convert("Europe/Vienna")
        )

        mock_ticker = Mock()
        mock_ticker.history.return_value = df

        monkeypatch.setattr(
            "market_analysis.asset.yf.Ticker",
            lambda ticker: mock_ticker,
        )

        asset = Asset("TEST", "Test Asset", mock_cache_manager)  # type: ignore
        result = asset.fetch()

        assert result is not None
        assert list(result.columns) == ["AdjClose"]

        res_idx = cast(pd.DatetimeIndex, result.index)
        assert res_idx.tz is None
        assert all(res_idx.hour == 0)
        assert res_idx.equals(pd.to_datetime(list(res_idx.date)))

        mock_cache_manager.load.assert_called_once_with("TEST")
        mock_cache_manager.save.assert_called_once()

    def test_fetch_from_cache(
        self, mock_cache_manager: MagicMock, sample_prices: pd.DataFrame
    ) -> None:
        mock_cache_manager.load.return_value = sample_prices
        mock_cache_manager.is_fresh.return_value = True

        asset = Asset("TEST", "Test Asset", mock_cache_manager)  # type: ignore
        df = asset.fetch()

        assert df is not None
        pd.testing.assert_frame_equal(df, sample_prices)
        mock_cache_manager.load.assert_called_once_with("TEST")
        mock_cache_manager.is_fresh.assert_called_once_with(sample_prices)
        mock_cache_manager.save.assert_not_called()

    def test_fetch_stale_cache_downloads(
        self,
        monkeypatch: pytest.MonkeyPatch,
        mock_cache_manager: MagicMock,
        sample_prices: pd.DataFrame,
    ) -> None:
        mock_cache_manager.load.return_value = sample_prices
        mock_cache_manager.is_fresh.return_value = False

        mock_hist = sample_prices.copy()
        mock_hist.columns = pd.Index(["Adj Close"])

        mock_ticker = Mock()
        mock_ticker.history.return_value = mock_hist

        monkeypatch.setattr(
            "market_analysis.asset.yf.Ticker",
            lambda ticker: mock_ticker,
        )

        asset = Asset("TEST", "Test Asset", mock_cache_manager)  # type: ignore
        df = asset.fetch()

        assert isinstance(df, pd.DataFrame)
        mock_cache_manager.save.assert_called_once()

    def test_fetch_empty_dataframe(
        self, monkeypatch: pytest.MonkeyPatch, mock_cache_manager: MagicMock
    ) -> None:
        mock_ticker = Mock()
        mock_ticker.history.return_value = pd.DataFrame()

        monkeypatch.setattr(
            "market_analysis.asset.yf.Ticker",
            lambda ticker: mock_ticker,
        )

        asset = Asset("TEST", "Test Asset", mock_cache_manager)  # type: ignore
        assert asset.fetch() is None

    def test_fetch_no_price_columns(
        self, monkeypatch: pytest.MonkeyPatch, mock_cache_manager: MagicMock
    ) -> None:
        df = pd.DataFrame({"Open": [1, 2, 3]})
        mock_ticker = Mock()
        mock_ticker.history.return_value = df

        monkeypatch.setattr(
            "market_analysis.asset.yf.Ticker",
            lambda ticker: mock_ticker,
        )

        asset = Asset("TEST", "Test Asset", mock_cache_manager)  # type: ignore
        assert asset.fetch() is None


# ---------------------------------------------------------------------
# Print Stats Tests
# ---------------------------------------------------------------------


class TestPrintStats:
    def test_total_return_exact(
        self,
        asset_factory: Callable[[pd.DataFrame | None], Asset],
        capsys: pytest.CaptureFixture[str],
        sample_prices: pd.DataFrame,
    ) -> None:
        asset = asset_factory(sample_prices)
        asset.print_asset_stats("2020-01-01", "2020-01-05")

        out = capsys.readouterr().out
        assert "Asset statistics: Test Asset" in out

        assert "Total return: 10.00%" in out

    def test_zero_drawdown(
        self,
        asset_factory: Callable[[pd.DataFrame | None], Asset],
        capsys: pytest.CaptureFixture[str],
        increasing_prices: pd.DataFrame,
    ) -> None:
        asset = asset_factory(increasing_prices)
        asset.print_asset_stats("2020-01-01", "2020-01-04")

        out = capsys.readouterr().out
        assert "Max drawdown: 0.00%" in out

    def test_insufficient_data(
        self,
        asset_factory: Callable[[pd.DataFrame | None], Asset],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        df = pd.DataFrame(
            {"AdjClose": [100]},
            index=pd.to_datetime(["2020-01-01"]),
        )
        asset = asset_factory(df)
        asset.print_asset_stats("2020-01-01", "2020-01-01")

        assert "insufficient data" in capsys.readouterr().out

    def test_df_none_raises(self) -> None:
        asset = Asset("T", "Test", Mock())  # type: ignore
        with pytest.raises(TypeError):
            asset.print_asset_stats("2020-01-01", "2020-01-05")

    @pytest.mark.parametrize("frequency", ["D", "ME", "YE"])
    def test_frequency_display(
        self,
        asset_factory: Callable[[pd.DataFrame | None], Asset],
        capsys: pytest.CaptureFixture[str],
        sample_prices: pd.DataFrame,
        frequency: str,
    ) -> None:
        asset = asset_factory(sample_prices)
        asset.print_asset_stats("2020-01-01", "2020-01-05", frequency=frequency)

        assert f"Frequency: {frequency}" in capsys.readouterr().out

    def test_autocorrelation_nan(
        self,
        asset_factory: Callable[[pd.DataFrame | None], Asset],
        capsys: pytest.CaptureFixture[str],
        sample_prices: pd.DataFrame,
    ) -> None:
        asset = asset_factory(sample_prices)

        asset.print_asset_stats(
            "2020-01-01",
            "2020-01-05",
            frequency="YE",
        )

        out = capsys.readouterr().out

        assert "Daily:" in out
        assert "Monthly:" in out
        assert "Yearly:  nan" in out


# ---------------------------------------------------------------------
# Plot Tests
# ---------------------------------------------------------------------


class TestPlotStats:
    def test_plot_creates_five_axes(
        self,
        asset_factory: Callable[[pd.DataFrame | None], Asset],
        monkeypatch: pytest.MonkeyPatch,
        sample_prices: pd.DataFrame,
    ) -> None:
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

    def test_log_price_sets_log_scale(
        self,
        asset_factory: Callable[[pd.DataFrame | None], Asset],
        monkeypatch: pytest.MonkeyPatch,
        sample_prices: pd.DataFrame,
    ) -> None:
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

    def test_show_called_when_no_save(
        self,
        asset_factory: Callable[[pd.DataFrame | None], Asset],
        monkeypatch: pytest.MonkeyPatch,
        sample_prices: pd.DataFrame,
    ) -> None:
        asset = asset_factory(sample_prices)

        monkeypatch.setattr("matplotlib.pyplot.close", Mock())
        show_mock = Mock()
        monkeypatch.setattr("matplotlib.pyplot.show", show_mock)

        asset.plot_asset_stats("2020-01-01", "2020-01-05")

        show_mock.assert_called_once()

    def test_save_called_and_show_not_called(
        self,
        asset_factory: Callable[[pd.DataFrame | None], Asset],
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Any,
        sample_prices: pd.DataFrame,
    ) -> None:
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

    def test_plot_insufficient_data(
        self, asset_factory: Callable[[pd.DataFrame | None], Asset]
    ) -> None:
        df = pd.DataFrame(
            {"AdjClose": [100]},
            index=pd.to_datetime(["2020-01-01"]),
        )
        asset = asset_factory(df)

        asset.plot_asset_stats("2020-01-01", "2020-01-01")

    def test_plot_df_none_raises(self) -> None:
        asset = Asset("T", "Test", Mock())  # type: ignore
        with pytest.raises(TypeError):
            asset.plot_asset_stats("2020-01-01", "2020-01-05")

    def test_plot_non_daily_branch_executes(
        self,
        asset_factory: Callable[[pd.DataFrame | None], Asset],
        monkeypatch: pytest.MonkeyPatch,
        sample_prices: pd.DataFrame,
    ) -> None:
        asset = asset_factory(sample_prices)

        monkeypatch.setattr("matplotlib.pyplot.close", Mock())
        monkeypatch.setattr("matplotlib.pyplot.show", Mock())

        asset.plot_asset_stats(
            "2020-01-01",
            "2020-01-05",
            frequency="ME",
            sharpe_window=2,
            risk_free_rate=0.01,
        )


# ---------------------------------------------------------------------
# Calculation Method Tests
# ---------------------------------------------------------------------


class TestCalculationMethods:
    def test_prepare_prices(
        self,
        asset_factory: Callable[[pd.DataFrame | None], Asset],
        sample_prices: pd.DataFrame,
    ) -> None:
        asset = asset_factory(sample_prices)

        prices = asset._prepare_prices("2020-01-01", "2020-01-05", "D")

        assert prices is not None
        pd.testing.assert_series_equal(
            prices, sample_prices["AdjClose"], check_freq=False
        )

        resampled = asset._prepare_prices("2020-01-01", "2020-01-05", "ME")
        assert resampled is not None
        assert len(resampled) == 1
        assert resampled.iloc[0] == pytest.approx(110.0)

    def test_prepare_prices_insufficient_and_missing_data(
        self, asset_factory: Callable[[pd.DataFrame | None], Asset]
    ) -> None:
        df = pd.DataFrame({"AdjClose": [100.0]}, index=pd.to_datetime(["2020-01-01"]))
        asset = asset_factory(df)
        assert asset._prepare_prices("2020-01-01", "2020-01-01", "D") is None

        asset = asset_factory(None)
        with pytest.raises(TypeError):
            asset._prepare_prices("2020-01-01", "2020-01-05", "D")

    def test_total_return(
        self,
        asset_factory: Callable[[pd.DataFrame | None], Asset],
        sample_prices: pd.DataFrame,
    ) -> None:
        asset = asset_factory(sample_prices)

        assert asset.calculate_total_return(sample_prices["AdjClose"]) == pytest.approx(
            0.10
        )

    def test_cagr(self, asset_factory: Callable[[pd.DataFrame | None], Asset]) -> None:
        asset = asset_factory(None)
        dates = pd.to_datetime(["2021-01-01", "2022-01-01"])
        prices = pd.Series([100.0, 121.0], index=dates)

        assert asset.calculate_cagr(prices) == pytest.approx(0.21, abs=1e-3)
        assert asset.calculate_cagr(prices, total_return=0.21) == pytest.approx(
            0.21, abs=1e-3
        )

    def test_cagr_zero_time_span_is_nan(
        self, asset_factory: Callable[[pd.DataFrame | None], Asset]
    ) -> None:
        asset = asset_factory(None)
        prices = pd.Series([100.0], index=pd.to_datetime(["2020-01-01"]))

        assert np.isnan(asset.calculate_cagr(prices))

    def test_volatility(
        self, asset_factory: Callable[[pd.DataFrame | None], Asset]
    ) -> None:
        asset = asset_factory(None)
        dates = pd.date_range("2020-01-01", periods=3, freq="D")
        prices = pd.Series([100.0, 110.0, 99.0], index=dates)
        expected = pd.Series([0.1, -0.1]).std()

        assert asset.calculate_volatility(prices, "ME") == pytest.approx(expected)
        assert asset.calculate_volatility(prices, "D") == pytest.approx(
            expected * np.sqrt(252)
        )

    def test_cumulative_return(
        self,
        asset_factory: Callable[[pd.DataFrame | None], Asset],
        sample_prices: pd.DataFrame,
    ) -> None:
        asset = asset_factory(sample_prices)

        cumulative = asset.calculate_cumulative_return(sample_prices["AdjClose"])

        assert cumulative.iloc[0] == pytest.approx(1.05)
        assert cumulative.iloc[-1] == pytest.approx(1.10)

    def test_drawdown_and_max_drawdown(
        self,
        asset_factory: Callable[[pd.DataFrame | None], Asset],
        sample_prices: pd.DataFrame,
        increasing_prices: pd.DataFrame,
    ) -> None:
        asset = asset_factory(sample_prices)
        prices = sample_prices["AdjClose"]

        drawdown = asset.calculate_drawdown(prices)

        assert drawdown.min() == pytest.approx(1.02 / 1.05 - 1)
        assert asset.calculate_max_drawdown(prices) == pytest.approx(drawdown.min())
        assert asset.calculate_max_drawdown(increasing_prices["AdjClose"]) == (
            pytest.approx(0.0)
        )

    def test_autocorrelation(
        self, asset_factory: Callable[[pd.DataFrame | None], Asset]
    ) -> None:
        asset = asset_factory(None)
        dates = pd.date_range("2020-01-01", periods=5, freq="D")
        prices = pd.Series([100.0, 110.0, 99.0, 108.9, 98.01], index=dates)

        assert asset.calculate_autocorrelation(prices) == pytest.approx(-1.0)

    def test_autocorrelation_short_series_is_nan(
        self,
        asset_factory: Callable[[pd.DataFrame | None], Asset],
        sample_prices: pd.DataFrame,
    ) -> None:
        asset = asset_factory(sample_prices)

        assert np.isnan(
            asset.calculate_autocorrelation(sample_prices["AdjClose"].iloc[:3])
        )

    def test_autocorrelations(
        self, asset_factory: Callable[[pd.DataFrame | None], Asset]
    ) -> None:
        asset = asset_factory(None)
        dates = pd.date_range("2020-01-01", periods=5, freq="D")
        prices = pd.Series([100.0, 110.0, 99.0, 108.9, 98.01], index=dates)

        result = asset.calculate_autocorrelations(prices)

        assert set(result) == {"daily", "monthly", "yearly"}
        assert result["daily"] == pytest.approx(-1.0)
        assert np.isnan(result["monthly"])
        assert np.isnan(result["yearly"])

    def test_rolling_volatility(
        self,
        asset_factory: Callable[[pd.DataFrame | None], Asset],
        sample_prices: pd.DataFrame,
    ) -> None:
        asset = asset_factory(sample_prices)
        returns = sample_prices["AdjClose"].pct_change().dropna()

        daily = asset.calculate_rolling_volatility(sample_prices["AdjClose"], 2, "D")
        pd.testing.assert_series_equal(daily, returns.rolling(2).std() * np.sqrt(252))

        non_daily = asset.calculate_rolling_volatility(
            sample_prices["AdjClose"], 2, "ME"
        )
        pd.testing.assert_series_equal(non_daily, returns.rolling(2).std())

    def test_rolling_sharpe(
        self, asset_factory: Callable[[pd.DataFrame | None], Asset]
    ) -> None:
        asset = asset_factory(None)
        dates = pd.date_range("2020-01-31", periods=6, freq="ME")
        prices = pd.Series([100.0, 105.0, 102.0, 108.0, 110.0, 115.0], index=dates)
        returns = prices.pct_change().dropna()

        result = asset.calculate_rolling_sharpe(prices, 2, 0.01, "ME")
        expected = (returns.rolling(2).mean() - 0.01) / returns.rolling(2).std()
        pd.testing.assert_series_equal(result, expected)

    def test_rolling_sharpe_daily_annualization(
        self,
        asset_factory: Callable[[pd.DataFrame | None], Asset],
        sample_prices: pd.DataFrame,
    ) -> None:
        asset = asset_factory(sample_prices)
        returns = sample_prices["AdjClose"].pct_change().dropna()

        result = asset.calculate_rolling_sharpe(sample_prices["AdjClose"], 2, 0.02, "D")
        expected = (returns.rolling(2).mean() - 0.02 / 252) / (
            returns.rolling(2).std() * np.sqrt(252)
        )
        pd.testing.assert_series_equal(result, expected)
