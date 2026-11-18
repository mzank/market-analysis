"""
Asset module for downloading, caching, analyzing, and visualizing
historical price data for financial instruments.

This module defines the Asset class, which encapsulates data retrieval
via yfinance, caching via CacheManager, and statistical analysis, and
visualization of price time series.
"""

import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf
from pandas._typing import TimestampConvertibleTypes

from .cachemanager import CacheManager
from .utils import safe_filename


class Asset:
    """
    Represent a financial asset with historical price data.

    An Asset handles downloading historical data, caching it locally,
    computing summary statistics and generating standard financial plots.
    """

    def __init__(self, ticker: str, label: str, cache_manager: CacheManager) -> None:
        """
        Initialize an Asset instance.

        Parameters
        ----------
        ticker : str
            The market ticker symbol (e.g., "^ATX", "^GSPC", "BTC-USD").
        label : str
            Name of the asset.
        cache_manager : CacheManager
            Instance responsible for loading and saving cached data.
        """

        self.ticker = ticker
        self.label = label
        self.cache_manager = cache_manager
        self.df: pd.DataFrame | None = None

    def fetch(self) -> pd.DataFrame | None:
        """
        Fetch historical price data for the asset.

        The method first attempts to load cached data. If no valid or
        fresh cache is available, data is downloaded using yfinance.
        Exchange-local dates are preserved; timezone information is dropped
        and dates are normalized to midnight.

        Returns
        -------
        pandas.DataFrame | None
            DataFrame containing an "AdjClose" column indexed by date.
            Returns None if data could not be retrieved.
        """

        # Attempt cache load
        cached = self.cache_manager.load(self.ticker)
        if cached is not None and self.cache_manager.is_fresh(cached):
            self.df = cached
            return self.df

        # Fetch fresh data
        print(f"Downloading data for {self.ticker}")
        hist = yf.Ticker(self.ticker).history(period="max")
        if hist.empty:
            return None

        # Prefer Adjusted Close
        if "Adj Close" in hist.columns:
            df = hist[["Adj Close"]].rename(columns={"Adj Close": "AdjClose"})
        elif "Close" in hist.columns:
            df = hist[["Close"]].rename(columns={"Close": "AdjClose"})
        else:
            print(f"No usable price column for {self.ticker}")
            return None

        idx = pd.to_datetime(hist.index)

        # Preserve the original exchange dates and remove timezone information
        if idx.tz is not None:
            idx = idx.tz_localize(None)
        idx = idx.normalize()

        df.index = idx
        self.df = df

        self.cache_manager.save(df, self.ticker)
        return self.df

    def _prepare_prices(
        self,
        start_date: TimestampConvertibleTypes,
        end_date: TimestampConvertibleTypes,
        frequency: str,
    ) -> pd.Series | None:
        """
        Select and optionally resample prices for the requested period.

        Parameters
        ----------
        start_date : TimestampConvertibleTypes
            Start date of the analysis period.
        end_date : TimestampConvertibleTypes
            End date of the analysis period.
        frequency : str
            Resampling frequency (e.g., "D", "ME", "YE").

        Returns
        -------
        pandas.Series | None
            Prepared price series, or None if fewer than two prices are
            available in the requested period before resampling. After
            resampling, the returned series may contain fewer observations.

        Raises
        ------
        TypeError
            If fetch() has not been called or no data is available.
        """

        if self.df is None:
            raise TypeError(f"No data available for {self.label}. Call fetch() first.")

        start = pd.Timestamp(start_date)
        end = pd.Timestamp(end_date)

        prices = self.df["AdjClose"].loc[start:end].copy()

        if prices.empty or len(prices) < 2:
            return None

        if frequency != "D":
            prices = prices.resample(frequency).last()

        return prices

    def _returns(self, prices: pd.Series) -> pd.Series:
        """
        Compute simple period returns from a price series.

        Parameters
        ----------
        prices : pandas.Series
            Price series.

        Returns
        -------
        pandas.Series
            Percentage changes with missing values removed.
        """

        return prices.pct_change().dropna()

    def calculate_total_return(self, prices: pd.Series) -> float:
        """
        Calculate the total return over a price series.

        Parameters
        ----------
        prices : pandas.Series
            Price series.

        Returns
        -------
        float
            Return from the first to the last price.
        """

        return float(prices.iloc[-1] / prices.iloc[0] - 1)

    def calculate_cagr(
        self, prices: pd.Series, total_return: float | None = None
    ) -> float:
        """
        Calculate the compound annual growth rate of a price series.

        Parameters
        ----------
        prices : pandas.Series
            Price series.
        total_return : float | None, default None
            Precomputed total return; calculated from prices when omitted.

        Returns
        -------
        float
            Annualized growth rate, or NaN for a zero/negative time span.
        """

        if total_return is None:
            total_return = self.calculate_total_return(prices)

        start = pd.Timestamp(prices.index[0])
        end = pd.Timestamp(prices.index[-1])
        n_years = (end - start).days / 365.25

        if n_years <= 0:
            return float("nan")

        return float((1 + total_return) ** (1 / n_years) - 1)

    def calculate_volatility(self, prices: pd.Series, frequency: str = "D") -> float:
        """
        Calculate the volatility of returns over a price series.

        Parameters
        ----------
        prices : pandas.Series
            Price series.
        frequency : str, default "D"
            Sampling frequency; daily returns are annualized with sqrt(252).

        Returns
        -------
        float
            Standard deviation of returns (annualized for daily data).
        """

        volatility = self._returns(prices).std()

        if frequency == "D":
            return float(volatility * np.sqrt(252))

        return float(volatility)

    def calculate_cumulative_return(self, prices: pd.Series) -> pd.Series:
        """
        Calculate the cumulative return series.

        Parameters
        ----------
        prices : pandas.Series
            Price series.

        Returns
        -------
        pandas.Series
            Cumulative growth factor of 1 plus returns.
        """

        return (1 + self._returns(prices)).cumprod()

    def calculate_drawdown(self, prices: pd.Series) -> pd.Series:
        """
        Calculate the drawdown series.

        Parameters
        ----------
        prices : pandas.Series
            Price series.

        Returns
        -------
        pandas.Series
            Relative decline from the running maximum price, including the
            first price as a possible peak.
        """

        return prices / prices.cummax() - 1

    def calculate_max_drawdown(self, prices: pd.Series) -> float:
        """
        Calculate the maximum drawdown of a price series.

        Parameters
        ----------
        prices : pandas.Series
            Price series.

        Returns
        -------
        float
            Largest peak-to-trough decline (zero or negative).
        """

        return float(self.calculate_drawdown(prices).min())

    def calculate_autocorrelation(
        self, prices: pd.Series, frequency: str = "D"
    ) -> float:
        """
        Calculate lag-1 autocorrelation of returns.

        Parameters
        ----------
        prices : pandas.Series
            Price series.
        frequency : str, default "D"
            Frequency used to resample prices before computing returns.

        Returns
        -------
        float
            Lag-1 autocorrelation, or NaN for fewer than three returns.
        """

        data = prices.resample(frequency).last() if frequency != "D" else prices
        returns = self._returns(data)

        if len(returns) < 3:
            return float("nan")

        return float(returns.autocorr(1))

    def calculate_autocorrelations(self, prices: pd.Series) -> dict[str, float]:
        """
        Calculate daily, monthly, and yearly return autocorrelations.

        Parameters
        ----------
        prices : pandas.Series
            Price series.

        Returns
        -------
        dict[str, float]
            Lag-1 autocorrelations keyed by "daily", "monthly", "yearly".

        Notes
        -----
        Pass native-frequency (unresampled) prices. Resampling for the
        monthly and yearly variants happens internally; passing already
        resampled data would mislabel the results.
        """

        return {
            "daily": self.calculate_autocorrelation(prices, "D"),
            "monthly": self.calculate_autocorrelation(prices, "ME"),
            "yearly": self.calculate_autocorrelation(prices, "YE"),
        }

    def calculate_rolling_volatility(
        self, prices: pd.Series, window: int, frequency: str = "D"
    ) -> pd.Series:
        """
        Calculate rolling volatility of returns.

        Parameters
        ----------
        prices : pandas.Series
            Price series.
        window : int
            Rolling window size.
        frequency : str, default "D"
            Sampling frequency; daily returns are annualized with sqrt(252).

        Returns
        -------
        pandas.Series
            Rolling volatility series.
        """

        rolling = self._returns(prices).rolling(window).std()

        if frequency == "D":
            return rolling * np.sqrt(252)

        return rolling

    def calculate_rolling_sharpe(
        self,
        prices: pd.Series,
        window: int,
        risk_free_rate: float,
        frequency: str = "D",
    ) -> pd.Series:
        """
        Calculate the rolling Sharpe ratio.

        Parameters
        ----------
        prices : pandas.Series
            Price series.
        window : int
            Rolling window size.
        risk_free_rate : float
            Annualized risk-free rate.
        frequency : str, default "D"
            Sampling frequency; determines the annualization of the rate
            and the volatility used in the denominator.

        Returns
        -------
        pandas.Series
            Rolling Sharpe ratio series.
        """

        rf_period = risk_free_rate / 252 if frequency == "D" else risk_free_rate
        rolling_vol = self.calculate_rolling_volatility(prices, window, frequency)
        rolling_mean = self._returns(prices).rolling(window).mean()

        return (rolling_mean - rf_period) / rolling_vol

    def print_asset_stats(
        self,
        start_date: TimestampConvertibleTypes,
        end_date: TimestampConvertibleTypes,
        frequency: str = "D",
    ) -> None:
        """
        Print summary statistics for the asset within a date range.

        Statistics include total return, CAGR, annualized volatility,
        maximum drawdown, and autocorrelation (daily, monthly, yearly).

        Parameters
        ----------
        start_date : TimestampConvertibleTypes
            Start date of the analysis period. Accepts any pandas-compatible
            datetime input (e.g. str, datetime, date, Timestamp).
        end_date : TimestampConvertibleTypes
            End date of the analysis period. Accepts any pandas-compatible
            datetime input (e.g. str, datetime, date, Timestamp).
        frequency : str, default "D"
            Resampling frequency (e.g., "D", "ME", "YE").

        Raises
        ------
        TypeError
            If fetch() has not been called or no data is available.

        Returns
        -------
        None
        """

        prices = self._prepare_prices(start_date, end_date, frequency)
        raw_prices = self._prepare_prices(start_date, end_date, "D")

        if prices is None or raw_prices is None:
            print(
                f"\n{self.label}: insufficient data between {start_date} and {end_date}"
            )
            return

        start_price = prices.iloc[0]
        end_price = prices.iloc[-1]
        total_return = self.calculate_total_return(prices)
        cagr = self.calculate_cagr(prices, total_return)
        vol_annualized = self.calculate_volatility(prices, frequency)
        max_dd = self.calculate_max_drawdown(prices)
        # Autocorrelations are always reported at daily/monthly/yearly
        # frequency, so compute them from the unresampled prices.
        auto_correlation = self.calculate_autocorrelations(raw_prices)

        print("\n" + "-" * 80)
        print(f"Asset statistics: {self.label}")
        print("-" * 80)
        print(f"Period: {prices.index[0].date()} - {prices.index[-1].date()}")
        print(f"Frequency: {frequency}")
        print(f"Observations: {len(prices)}")
        print(f"Start price: {start_price:.2f}")
        print(f"End price:   {end_price:.2f}")
        print(f"Total return: {total_return:.2%}")
        print(f"CAGR:         {cagr:.2%}")
        print(f"Volatility:   {vol_annualized:.2%}")
        print(f"Max drawdown: {max_dd:.2%}")
        print("Autocorrelation:")
        print(f"  Daily:   {auto_correlation['daily']:.4f}")
        print(f"  Monthly: {auto_correlation['monthly']:.4f}")
        print(f"  Yearly:  {auto_correlation['yearly']:.4f}")
        print("-" * 80)

    def plot_asset_stats(
        self,
        start_date: TimestampConvertibleTypes,
        end_date: TimestampConvertibleTypes,
        frequency: str = "D",
        log_price: bool = False,
        sharpe_window: int = 63,
        risk_free_rate: float = 0.0,
        figsize: tuple[float, float] = (10, 10),
        save_path: str | None = None,
    ) -> None:
        """
        Plot key performance metrics for the asset.

        The generated figure includes:
        - Price series
        - Cumulative return
        - Drawdown
        - Rolling volatility
        - Rolling Sharpe ratio

        Parameters
        ----------
        start_date : TimestampConvertibleTypes
            Start date of the analysis period. Accepts any pandas-compatible
            datetime input (e.g. str, datetime, date, Timestamp).
        end_date : TimestampConvertibleTypes
            End date of the analysis period. Accepts any pandas-compatible
            datetime input (e.g. str, datetime, date, Timestamp).
        frequency : str, default "D"
            Resampling frequency.
        log_price : bool, default False
            If True, uses logarithmic scale for price axis.
        sharpe_window : int, default 63
            Rolling window size for volatility and Sharpe ratio.
        risk_free_rate : float, default 0.0
            Annualized risk-free rate used in Sharpe ratio calculation.
        figsize : tuple[float, float], default (10, 10)
            Figure size in inches as (width, height).
        save_path : str | None, default None
            If provided, saves the plot to this path; otherwise displays it.

        Raises
        ------
        TypeError
            If fetch() has not been called or no data is available.

        Returns
        -------
        None
        """

        prices = self._prepare_prices(start_date, end_date, frequency)

        if prices is None:
            print(f"{self.label}: insufficient data to plot.")
            return

        cumulative = self.calculate_cumulative_return(prices)
        drawdown = self.calculate_drawdown(prices)
        rolling_vol = self.calculate_rolling_volatility(
            prices, sharpe_window, frequency
        )
        rolling_sharpe = self.calculate_rolling_sharpe(
            prices, sharpe_window, risk_free_rate, frequency
        )

        fig, axes = plt.subplots(5, 1, figsize=figsize, sharex=True)

        # --- Titel ---
        fig.suptitle(
            f"{self.label} (ticker: {self.ticker}, frequency: {frequency})\n"
            f"{prices.index[0].date()} - {prices.index[-1].date()}",
            fontsize=16,
            fontweight="bold",
        )

        # --- Price ---
        axes[0].plot(prices.index, prices, color="black")
        axes[0].set_title("Price")
        axes[0].grid(True, alpha=0.3)

        if log_price:
            axes[0].set_yscale("log")
            axes[0].set_ylabel("Log price")

        # --- Cumulative return ---
        axes[1].plot(cumulative.index, cumulative - 1, color="blue")
        axes[1].set_title("Cumulative return")
        axes[1].yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0%}"))
        axes[1].grid(True, alpha=0.3)

        # --- Drawdown ---
        axes[2].fill_between(drawdown.index, drawdown, 0, color="red", alpha=0.3)
        axes[2].set_title("Drawdown")
        axes[2].yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0%}"))
        axes[2].grid(True, alpha=0.3)

        # --- Rolling volatility ---
        axes[3].plot(rolling_vol.index, rolling_vol, color="purple")
        axes[3].set_title(f"Rolling volatility ({sharpe_window} days)")
        axes[3].yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0%}"))
        axes[3].grid(True, alpha=0.3)

        # --- Rolling sharpe ratio ---
        axes[4].plot(rolling_sharpe.index, rolling_sharpe, color="green")
        axes[4].axhline(0, color="black", lw=1)
        axes[4].set_title(
            f"Rolling sharpe ratio ({sharpe_window} days, "
            f"risk free rate {risk_free_rate*100} % p.a.)"
        )
        axes[4].grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            # separate dir and filename
            dir_name = os.path.dirname(save_path)
            file_name = os.path.basename(save_path)
            file_name = safe_filename(file_name)
            save_path = os.path.join(dir_name, file_name)
            plt.savefig(save_path, dpi=150)
            print(f"Saved asset stats plot to {save_path}")
        else:
            plt.show()

        plt.close()
