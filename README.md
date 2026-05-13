# Momentum-Based Quantitative Portfolio Platform

A fully automated quantitative fintech platform that applies **risk-adjusted momentum factor investing** to the NIFTY 100 stock universe.

---

## Strategy Summary

| Parameter | Value |
|---|---|
| Universe | NIFTY 100 (NSE India) |
| Strategy | Risk-Adjusted Momentum (Return / Volatility) |
| Portfolio | Top 20 stocks, equal-weight (5% each) |
| Rebalancing | Quarterly (Mar / Jun / Sep / Dec) |
| Initial Capital | ₹10,00,000 |
| Benchmark | NIFTY 100 Index (^CNX100) |
| Backtest Period | Jan 2023 – May 2026 (3 years out-of-sample) |

---

## Results

| Metric | Strategy | Benchmark |
|---|---|---|
| Final Value | ₹20,00,262 | ₹13,25,551 |
| CAGR | 23.49% | 8.96% |
| Sharpe Ratio | 0.976 | 0.262 |
| Max Drawdown | -27.85% | -17.53% |
| Alpha | +14.53% | — |
| Hypothesis Test | ✅ Reject H0 (p = 0.0117) | — |

---

## How It Works

### Momentum Score Formula

```
Momentum Score = R_252 / sigma_annual

where:
  R_252        = (Price_today - Price_252days_ago) / Price_252days_ago
  sigma_annual = std(daily_returns) * sqrt(252)
```

### Rebalance Logic
- **Signal date:** Last trading day of each quarter (compute scores)
- **Execution date:** First trading day of next quarter (execute trades)
- This one-day lag eliminates look-ahead bias

---

## Project Structure

```
momentum_platform/
  data/
    raw/              <- Downloaded price CSVs (one per ticker)
    processed/        <- Cleaned data
    tickers/          <- nifty100_tickers.csv
  outputs/
    charts/           <- Saved charts
    metrics/          <- backtest_results.csv, download_log.csv
    holdings/         <- Quarterly holdings snapshots
    reports/          <- Summary reports
  src/
    data_fetch.py     <- Downloads 4 years of data from Yahoo Finance
    momentum.py       <- Computes R_252, volatility, momentum scores
    backtest.py       <- Daily NAV simulation, benchmark tracking
    metrics.py        <- CAGR, Sharpe, Drawdown, Alpha, t-test
  dashboard/
    streamlit_app.py  <- Interactive Streamlit dashboard
  main.py
  requirements.txt
  README.md
```

---

## Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/momentum_platform.git
cd momentum_platform
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Download stock data
```bash
python src/data_fetch.py
```

### 4. Run the backtest and metrics
```bash
python src/metrics.py
```

### 5. Launch the dashboard
```bash
streamlit run dashboard/streamlit_app.py
```

---

## Key Files

| File | Purpose |
|---|---|
| `src/data_fetch.py` | Downloads NIFTY 100 price data from Yahoo Finance with retry logic |
| `src/momentum.py` | Computes risk-adjusted momentum scores at each quarter-end |
| `src/backtest.py` | Simulates daily portfolio value over 3-year backtest period |
| `src/metrics.py` | Calculates CAGR, Sharpe, Max Drawdown, Alpha, paired t-test |
| `dashboard/streamlit_app.py` | Full interactive investor dashboard |

---

## Known Limitations

- **Survivorship Bias:** Uses current NIFTY 100 composition — stocks removed historically are excluded
- **No Transaction Costs:** Real brokerage fees (~0.2–0.5% per round trip) not modeled
- **No Slippage:** Execution assumed at exact closing price
- **Fractional Shares:** Allowed in simulation; most Indian brokers don't support this

---

## Tech Stack

Python · Pandas · NumPy · SciPy · yfinance · Plotly · Streamlit

---

## Disclaimer

This project is for **academic and educational purposes only**. It does not constitute financial advice. Past simulated performance does not guarantee future results.
