# Functional Overview

The `market-analysis` toolkit is designed to streamline the process of retrieving, caching, and analyzing financial market data. It bridges the gap between raw data providers and actionable financial insights by providing a robust framework for performance metrics and visualization.

## Core Workflow

The project follows a structured data processing sequence:

1.  **Data Fetching**: Interface with Yahoo Finance (`yfinance`) to retrieve historical OHLCV data.
2.  **Local Caching**: Persistence layer using Parquet files to minimize network requests and improve performance.
3.  **Asset Modeling**: Encapsulation of raw data into high-level `Asset` objects that handle statistical calculations.
4.  **Analysis**: Computation of key performance indicators like CAGR, Volatility, and Drawdowns.
5.  **Visualization**: Generation of multi-panel charts for visual correlation and trend analysis.

---

## Data Acquisition & Caching

The toolkit uses a "Fetch-Through" cache strategy managed by the `CacheManager`:

- **Local Storage**: Data is stored in the `cache_history/` directory using the Apache Parquet format (via `pyarrow`), providing high compression and fast read/write speeds.
- **Cache Validation**: The system checks the modification time of cached files. If the data is older than the configured `CACHE_MAX_AGE` (default: 1 day), it triggers a background refresh from Yahoo Finance.
- **Concurrent Fetching**: When loading multiple tickers, the `DataFetcher` utilizes a thread pool (`MAX_WORKERS`) to download data in parallel, significantly reducing wait times.

## Performance Metrics

The `Asset` class computes several critical financial metrics:

- **Returns**: Logarithmic and simple returns for various frequencies (Daily, Monthly, Yearly).
- **Risk Metrics**:
  - **Volatility**: Annualized standard deviation of returns.
  - **Maximum Drawdown**: The peak-to-trough decline during a specific period.
  - **Rolling Metrics**: Rolling volatility and Sharpe ratio (default 63-day window) to visualize risk evolution over time.
- **Growth Metrics**: Compound Annual Growth Rate (CAGR) and total cumulative returns.

## Visualization Engine

The toolkit generates a comprehensive five-panel chart for each asset:

1.  **Price Chart**: Raw closing prices, with optional logarithmic scaling.
2.  **Cumulative Returns**: Growth of a hypothetical $1 investment.
3.  **Drawdown Map**: Visualizes the depth and duration of "underwater" periods.
4.  **Rolling Volatility**: Tracks changes in asset risk profile over time.
5.  **Rolling Sharpe Ratio**: Displays the risk-adjusted return trend.

## Interface Options

### Command Line Interface (CLI)
Designed for quick checks and terminal-based analysis. It provides a summarized text report of an asset's performance directly in the console.

### Python API
Designed for integration into larger research projects or Jupyter notebooks. It offers full programmatic access to the `Asset` and `DataFetcher` classes, allowing for custom data manipulation and advanced plotting.
