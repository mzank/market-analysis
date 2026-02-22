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

from .utils import safe_filename


class Asset:
    """
    Represent a financial asset with historical price data.

    An Asset handles downloading historical data, caching it locally,
    computing summary statistics and generating standard financial plots.
    """

    def __init__(self, ticker, label, cache_manager):
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
        self.df = None

    def fetch(self):
        """
        Fetch historical price data for the asset.

        The method first attempts to load cached data. If no valid or
        fresh cache is available, data is downloaded using yfinance.
        Prices are normalized to UTC and stored as timezone-naive dates.

        Returns
        -------
        pandas.DataFrame or None
            DataFrame containing an "AdjClose" column indexed by date,
            or None if data could not be retrieved.
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
            self.df = hist[["Adj Close"]].rename(columns={"Adj Close": "AdjClose"})
        elif "Close" in hist.columns:
            self.df = hist[["Close"]].rename(columns={"Close": "AdjClose"})
        else:
            print(f"No usable price column for {self.ticker}")
            return None

        idx = pd.to_datetime(hist.index)

        # Normalize all assets to UTC and make tz-naive
        if idx.tz is not None:
            idx = idx.tz_convert("UTC").tz_localize(None)
        idx = idx.normalize()

        self.df.index = idx

        self.cache_manager.save(self.df, self.ticker)
        return self.df

    def print_asset_stats(self, start_date, end_date, frequency="D"):
        """
        Print summary statistics for the asset within a date range.

        Statistics include total return, CAGR, annualized volatility,
        maximum drawdown, and autocorrelation (daily, monthly, yearly).

        Parameters
        ----------
        start_date : str or datetime-like
            Start date of the analysis period.
        end_date : str or datetime-like
            End date of the analysis period.
        frequency : str, default "D"
            Resampling frequency (e.g., "D", "ME", "YE").

        Returns
        -------
        None
        """

        prices = self.df["AdjClose"].loc[start_date:end_date].copy()

        if prices.empty or len(prices) < 2:
            print(
                f"\n{self.label}: insufficient data between {start_date} and {end_date}"
            )
            return

        # Resample if needed
        if frequency != "D":
            prices = prices.resample(frequency).last()

        returns = prices.pct_change().dropna()

        # Stats
        start_price = prices.iloc[0]
        end_price = prices.iloc[-1]
        total_return = end_price / start_price - 1

        n_years = (prices.index[-1] - prices.index[0]).days / 365.25
        cagr = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else np.nan

        vol_annualized = (
            returns.std() * np.sqrt(252) if frequency == "D" else returns.std()
        )

        # Max drawdown
        cum = (1 + returns).cumprod()
        running_max = cum.cummax()
        drawdown = cum / running_max - 1
        max_dd = drawdown.min()

        # Autocorrelation
        ac_daily = prices.pct_change().dropna().autocorr(1)
        ac_monthly = prices.resample("ME").last().pct_change().dropna().autocorr(1)
        ac_yearly = prices.resample("YE").last().pct_change().dropna().autocorr(1)
        auto_correlation = {
            "daily": ac_daily,
            "monthly": ac_monthly,
            "yearly": ac_yearly,
        }

        print(
            "\n--------------------------------------------------------------------------------"
        )
        print(f"Asset statistics: {self.label}")
        print(
            "--------------------------------------------------------------------------------"
        )
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
        print(
            "--------------------------------------------------------------------------------"
        )

    def plot_asset_stats(
        self,
        start_date,
        end_date,
        frequency="D",
        log_price=False,
        sharpe_window=63,
        risk_free_rate=0.0,
        figsize=(10, 10),
        save_path=None,
    ):
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
        start_date : str or datetime-like
            Start date of the analysis period.
        end_date : str or datetime-like
            End date of the analysis period.
        frequency : str, default "D"
            Resampling frequency.
        log_price : bool, default False
            Whether to display the price axis on a logarithmic scale.
        sharpe_window : int, default 63
            Rolling window size for volatility and Sharpe ratio.
        risk_free_rate : float, default 0.0
            Annualized risk-free rate used for Sharpe ratio calculation.
        figsize : tuple, default (10, 10)
            Figure size passed to matplotlib.
        save_path : str or None, default None
            If provided, save the plot to this path instead of displaying it.

        Returns
        -------
        None
        """

        prices = self.df["AdjClose"].loc[start_date:end_date].copy()

        if prices.empty or len(prices) < 2:
            print(f"{self.label}: insufficient data to plot.")
            return

        # Resample if needed
        if frequency != "D":
            prices = prices.resample(frequency).last()

        returns = prices.pct_change().dropna()

        # --- Cumulative return ---
        cumulative = (1 + returns).cumprod()

        # --- Drawdown ---
        running_max = cumulative.cummax()
        drawdown = cumulative / running_max - 1

        # --- Rolling volatility ---
        if frequency == "D":
            rolling_vol = returns.rolling(sharpe_window).std() * np.sqrt(252)
            rf_period = risk_free_rate / 252
        else:
            rolling_vol = returns.rolling(sharpe_window).std()
            rf_period = risk_free_rate

        # --- Rolling Sharpe ratio ---
        rolling_mean = returns.rolling(sharpe_window).mean()
        rolling_sharpe = (rolling_mean - rf_period) / rolling_vol

        fig, axes = plt.subplots(5, 1, figsize=figsize, sharex=True)

        # --- Titel ---
        fig.suptitle(
            f"{self.label} (ticker: {self.ticker}, frequency: {frequency})\n{prices.index[0].date()} - {prices.index[-1].date()}",
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
            f"Rolling sharpe ratio ({sharpe_window} days, risk free rate {risk_free_rate*100} % p.a.)"
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
