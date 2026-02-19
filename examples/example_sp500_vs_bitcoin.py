"""
Example script: S&P 500 vs. Bitcoin analysis.

This example demonstrates how to use the ``market-analysis`` package
to download historical price data for the S&P 500 and Bitcoin,
compute performance statistics, and generate multi-panel performance
charts.

The script performs the following steps:

1. Configures ticker symbols and display labels.
2. Downloads and caches historical price data.
3. Prints performance statistics for each asset.
4. Generates and saves performance charts as PDF files.

The generated plots include:

- Price (log scale enabled)
- Cumulative return
- Drawdown
- Rolling volatility
- Rolling Sharpe ratio

Output files are saved as:

    Stats_<Asset Label>.pdf
"""

from market_analysis.datafetcher import DataFetcher


def main() -> None:
    """
    Run a comparative performance analysis for the S&P 500 and Bitcoin.

    The function downloads historical data for the configured assets,
    computes key performance metrics between the specified date range,
    and generates multi-panel performance charts.

    The Sharpe ratio is calculated using:
        - A rolling window of 126 trading days
        - A constant risk-free rate of 2%

    All generated charts are saved to disk as PDF files.
    """
    ticker_config = {
        "^GSPC": {"label": "S&P 500"},
        "BTC-USD": {"label": "Bitcoin"},
    }

    start_date = "2016-01-01"
    end_date = "2025-12-31"

    fetcher = DataFetcher(ticker_config)
    assets = fetcher.load_assets()

    for asset in assets.values():
        asset.print_asset_stats(start_date, end_date, frequency="ME")
        asset.plot_asset_stats(
            start_date=start_date,
            end_date=end_date,
            log_price=True,
            sharpe_window=126,
            risk_free_rate=0.02,
            save_path=f"Stats_{asset.label}.pdf",
        )


if __name__ == "__main__":
    main()
