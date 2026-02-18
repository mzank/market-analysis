"""
Command-line interface for the market_analysis project.

This module provides a CLI entry point that allows users to fetch
asset data and compute summary statistics over a specified date range.
"""

import argparse
from datetime import datetime

from .datafetcher import DataFetcher


def main():
    """
    Execute the command-line interface.

    Parses user-provided tickers and date range arguments, loads
    historical data, and prints summary statistics for each asset.

    Returns
    -------
    None
    """

    parser = argparse.ArgumentParser(description="Market Analysis Tool")

    parser.add_argument(
        "--tickers",
        nargs="+",
        required=True,
        help="List of tickers (e.g. ^ATX ^GSPC BTC-USD GC=F)",
    )

    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")

    parser.add_argument(
        "--end",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="End date (YYYY-MM-DD)",
    )

    args = parser.parse_args()

    ticker_config = {ticker: {"label": ticker} for ticker in args.tickers}

    fetcher = DataFetcher(ticker_config)
    assets = fetcher.load_assets()

    for asset in assets.values():
        asset.print_asset_stats(args.start, args.end, frequency="ME")
        asset.plot_asset_stats(
            start_date=args.start,
            end_date=args.end,
            log_price=True,
            sharpe_window=126,
            risk_free_rate=0.02,
            save_path=f"Stats_{asset.label}.pdf",
        )
