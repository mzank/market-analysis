# market-analysis

![Python](https://img.shields.io/badge/python-3-blue)
![License](https://img.shields.io/badge/license-Apache%202.0-green)

Financial asset analysis and correlation toolkit for Python.

`market-analysis` allows you to download historical price data, cache it locally, compute performance statistics, and generate professional financial charts.

---

## Features

- Download historical data via Yahoo Finance (`yfinance`)
- Local Parquet-based caching
- Performance metrics:
  - Total return
  - CAGR
  - Volatility
  - Maximum drawdown
  - Autocorrelation
- Multi-panel asset visualization
- Concurrent data fetching

---

## Caching

The project uses a local caching mechanism to avoid redundant downloads and improve performance when working with historical data.

### Cache Settings

The caching behavior is controlled by constants in `src/market_analysis/config.py`:

| Setting          | Default Value     | Description                                           |
| ---------------- | ----------------- | ----------------------------------------------------- |
| `CACHE_DIR`      | `"cache_history"` | Directory where cached data is stored.                |
| `CACHE_MAX_AGE`  | `1`               | Maximum cache age in days before data is refreshed.   |
| `SCHEMA_VERSION` | `"1.0"`           | Version of the cached data schema.                    |
| `PARQUET_ENGINE` | `"pyarrow"`       | Engine used for storing Parquet files.                |
| `MAX_WORKERS`    | `6`               | Maximum number of parallel threads for fetching data. |

*Note:* `MAX_WORKERS` controls the maximum number of concurrent threads when fetching data from Yahoo Finance, improving speed for multiple assets.

### Cache Location

According to the default config, downloaded data is stored locally in the following directory:

```text
cache_history/
```

This directory is created automatically in your working directory if it does not already exist.

### Cache Duration

According to the default config, cached data is considered valid for 1 day. After this period, the data will be refreshed automatically on the next request.

### Disabling Cache

Caching is always enabled by default. There is currently no CLI flag or configuration option to disable it temporarily.

To manually clear the cache, delete the cache directory:

```bash
rm -rf cache_history/
```

---

## Requirements

- Python >= 3.12

---

## Installation

### Install from source

```bash
git clone https://github.com/mzank/market-analysis.git
cd market-analysis
pip install -e .
```

### Install with development tools

```bash
pip install -e .[dev]
```

---

## Command Line Usage (CLI)

The CLI downloads data and prints performance statistics per asset. After installation, the CLI command is available:

```bash
market-analysis --tickers ^GSPC BTC-USD GC=F --start 2015-01-01
```

### Parameters

| Argument    | Description                         |
| ----------- | ----------------------------------- |
| `--tickers` | One or more asset tickers           |
| `--start`   | Start date (YYYY-MM-DD)             |
| `--end`     | End date (optional, default: today) |

### Examples

Single asset:
```bash
market-analysis --tickers ^GSPC --start 2020-01-01
```
Multiple assets:
```bash
market-analysis --tickers ^GSPC ^ATX BTC-USD --start 2018-01-01
```
With end date:
```bash
market-analysis --tickers ^GSPC --start 2010-01-01 --end 2020-01-01
```

---

## Python API Example

```python
from market_analysis import DataFetcher

ticker_config = {
    "^GSPC": {"label": "S&P 500"},
    "BTC-USD": {"label": "Bitcoin"},
}

fetcher = DataFetcher(ticker_config)
assets = fetcher.load_assets()

sp500 = assets["^GSPC"]

sp500.print_asset_stats(
    start_date="2015-01-01",
    end_date="2024-01-01",
    frequency="ME"
)

sp500.plot_asset_stats(
    start_date="2015-01-01",
    end_date="2024-01-01",
    frequency="D",
    log_price=True,
)
```

## Frequency Parameter

Several functions such as `print_asset_stats()` and `plot_asset_stats()` accept a `frequency` parameter to control the resampling interval used for return and risk calculations.

### Supported Frequency Options

| Value  | Description | Meaning                               |
| ------ | ----------- | ------------------------------------- |
| `"D"`  | Daily       | Uses daily data without resampling    |
| `"ME"` | Month End   | Resamples data to month-end frequency |
| `"YE"` | Year End    | Resamples data to year-end frequency  |

### Example

```python
sp500.print_asset_stats(
    start_date="2015-01-01",
    end_date="2024-01-01",
    frequency="ME",  # Monthly statistics
)
```

---

## Generated Plots

The visualization includes the following panels. Plots can be displayed or saved to disk:
1. Price (optional log-scale)
2. Cumulative return
3. Drawdown
4. Rolling volatility
5. Rolling Sharpe ratio

---

## Project Structure

```text
market-analysis/
│
├── examples/
│   └── example_sp500_vs_bitcoin.py
│
├── src/
│   └── market_analysis/
│       ├── __init__.py
│       ├── asset.py
│       ├── cachemanager.py
│       ├── cli.py
│       ├── config.py
│       ├── datafetcher.py
│       └── utils.py
│
├── tests/
│   ├── test_asset.py
│   ├── test_cachemanager.py
│   ├── test_cli.py
│   ├── test_datafetcher.py
│   └── test_utils.py
│
├── CITATION.cff
├── LICENSE
├── README.md
└── pyproject.toml
```

---

## Development

The project includes configuration for:
- black
- isort
- flake8
- pylint
- mypy
- pytest

### Formatting

Run formatting:
```bash
black .
isort .
```

### Static Analysis

Run static checks:
```bash
flake8
pylint src/
mypy src/
```

### Testing

The project uses `pytest` for automated testing.

Install development dependencies:
```bash
pip install -e .[dev]
```

Run tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=market_analysis --cov-report=term-missing
```

---

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.

You can also view the license here: https://www.apache.org/licenses/LICENSE-2.0

---
