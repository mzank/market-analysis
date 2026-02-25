# market-analysis

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

Example:
```bash
market-analysis \
  --tickers ^GSPC BTC-USD \
  --start 2018-01-01 \
  --end 2024-01-01
```

---

## Python API Example

```python
from market_analysis.datafetcher import DataFetcher

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
├── src/
│   └── market_analysis/
│       ├── asset.py
│       ├── cachemanager.py
│       ├── cli.py
│       ├── config.py
│       ├── datafetcher.py
│       └── utils.py
│
├── examples/
│   └── example_sp500_vs_bitcoin.py
│
├── tests/
│   ├── test_asset.py
│   ├── test_cachemanager.py
│   └── test_utils.py
│
├── pyproject.toml
└── README.md
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
pytest --cov=market_analysis
```

---

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.

You can also view the license here: https://www.apache.org/licenses/LICENSE-2.0

---
