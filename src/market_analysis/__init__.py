"""
market_analysis

A Python toolkit for downloading, caching, and analyzing financial market data.

The package provides a simple interface to retrieve historical asset prices,
compute performance metrics (e.g. return, volatility, drawdown), and generate
visualizations for financial analysis.

Public API:
    - DataFetcher: Load and manage multiple financial assets
    - Asset: Analyze and visualize individual asset performance
"""

from importlib.metadata import PackageNotFoundError, version

from .asset import Asset
from .datafetcher import DataFetcher

__all__ = [
    "DataFetcher",
    "Asset",
    "__version__",
]

try:
    # The version is defined once, in pyproject.toml.
    __version__ = version("market-analysis")
except PackageNotFoundError:  # running from an uninstalled source checkout
    __version__ = "0.0.0"
