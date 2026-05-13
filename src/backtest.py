# src/backtest.py
# Simulates the portfolio over 3 years, tracks daily value vs benchmark

import pandas as pd
import numpy as np
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.momentum import load_all_prices, get_quarter_end_dates, compute_momentum_score, get_top20

INITIAL_CAPITAL  = 1_000_000   # INR 10 Lakhs
BACKTEST_START   = "2023-01-01"
BENCHMARK_TICKER = "^CNX100"

def load_benchmark():
    """Loads the NIFTY 100 index data."""
    path = "data/raw/^CNX100.csv"
    if not os.path.exists(path):
        print("Benchmark file not found. Downloading...")
        import yfinance as yf
        data = yf.download("^CNX100", start="2022-01-01", end="2026-05-13",
                           auto_adjust=True, progress=False)
        s = data["Close"].dropna()
        s.to_csv(path, header=["close"])
        print(f"  ^CNX100: {len(s)} rows saved")

    df = pd.read_csv(path, index_col=0, parse_dates=True)
    df.columns = ["close"]
    return df["close"]


def get_execution_date(signal_date, all_dates):
    """Returns the first trading day AFTER the signal date."""
    future = all_dates[all_dates > signal_date]
    if len(future) == 0:
        return None
    return future[0]


def run_backtest():
    print("=" * 55)
    print("BACKTESTING ENGINE")
    print("=" * 55)

    # ── Load data ──────────────────────────────────────────────────
    prices       = load_all_prices()
    benchmark    = load_benchmark()
    all_dates    = prices.index
    quarter_ends = get_quarter_end_dates(prices, BACKTEST_START)

    # ── Restrict to backtest period ────────────────────────────────
    backtest_dates = all_dates[all_dates >= BACKTEST_START]

    # ── Storage ────────────────────────────────────────────────────
    portfolio_values  = []   # daily strategy NAV
    benchmark_values  = []   # daily benchmark NAV
    holdings_log      = []   # quarterly holdings snapshots
    daily_dates       = []

    # ── Initialize ─────────────────────────────────────────────────
    portfolio_cash    = INITIAL_CAPITAL
    current_holdings  = {}   # {ticker: shares}

    # Normalize benchmark to same starting capital
    bench_start_price = benchmark[benchmark.index >= BACKTEST_START].iloc[0]

    # Build rebalance schedule: {execution_date: signal_date}
    rebalance_schedule = {}
    for signal_date in quarter_ends:
        exec_date = get_execution_date(signal_date, all_dates)
        if exec_date is not None and exec_date >= pd.Timestamp(BACKTEST_START):
            rebalance_schedule[exec_date] = signal_date

    print(f"\nRebalance schedule ({len(rebalance_schedule)} events):")
    for exec_d, sig_d in rebalance_schedule.items():
        print(f"  Signal: {sig_d.date()}  →  Execute: {exec_d.date()}")

    # ── Main backtest loop ─────────────────────────────────────────
    print(f"\nRunning daily simulation from {backtest_dates[0].date()} "
          f"to {backtest_dates[-1].date()}...\n")

    for date in backtest_dates:

        # ── Rebalance if today is an execution date ────────────────
        if date in rebalance_schedule:
            signal_date = rebalance_schedule[date]

            # Safety check — look-ahead bias guard
            assert signal_date < date, f"Look-ahead bias! Signal {signal_date} >= Execution {date}"

            # Compute momentum scores on signal date
            scores = compute_momentum_score(prices, signal_date)

            if scores is not None:
                top20 = get_top20(scores)
                selected = top20.index.tolist()

                # Current portfolio value before rebalance
                if current_holdings:
                    port_val = sum(
                        shares * prices.loc[date, ticker]
                        for ticker, shares in current_holdings.items()
                        if ticker in prices.columns and not pd.isna(prices.loc[date, ticker])
                    )
                else:
                    port_val = portfolio_cash

                # Equal weight allocation
                n        = len(selected)
                per_stock = port_val / n

                # Buy new holdings
                new_holdings = {}
                for ticker in selected:
                    if ticker in prices.columns:
                        price = prices.loc[date, ticker]
                        if not pd.isna(price) and price > 0:
                            shares = per_stock / price
                            new_holdings[ticker] = shares

                current_holdings = new_holdings
                portfolio_cash   = 0

                # Log this rebalance
                holdings_log.append({
                    "rebalance_date" : date.date(),
                    "signal_date"    : signal_date.date(),
                    "holdings"       : selected,
                    "scores"         : top20["score"].to_dict()
                })

                print(f"  Rebalanced on {date.date()} using signal from {signal_date.date()} | {n} stocks")

        # ── Daily valuation ────────────────────────────────────────
        if current_holdings:
            port_val = sum(
                shares * prices.loc[date, ticker]
                for ticker, shares in current_holdings.items()
                if ticker in prices.columns and not pd.isna(prices.loc[date, ticker])
            )
        else:
            port_val = portfolio_cash

        # Benchmark value
        bench_price = benchmark.get(date, np.nan)
        if pd.isna(bench_price):
            # Use last available benchmark price
            available_bench = benchmark[benchmark.index <= date]
            bench_price = available_bench.iloc[-1] if len(available_bench) > 0 else bench_start_price

        bench_val = INITIAL_CAPITAL * (bench_price / bench_start_price)

        portfolio_values.append(port_val)
        benchmark_values.append(bench_val)
        daily_dates.append(date)

    # ── Build results DataFrame ────────────────────────────────────
    results = pd.DataFrame({
        "date"            : daily_dates,
        "portfolio_value" : portfolio_values,
        "benchmark_value" : benchmark_values
    }).set_index("date")

    results["portfolio_return"] = results["portfolio_value"].pct_change()
    results["benchmark_return"] = results["benchmark_value"].pct_change()

    # ── Save results ───────────────────────────────────────────────
    os.makedirs("outputs/metrics", exist_ok=True)
    results.to_csv("outputs/metrics/backtest_results.csv")
    print(f"\nResults saved to outputs/metrics/backtest_results.csv")

    # ── Quick summary ──────────────────────────────────────────────
    final_port  = results["portfolio_value"].iloc[-1]
    final_bench = results["benchmark_value"].iloc[-1]

    print(f"\n{'='*55}")
    print(f"BACKTEST SUMMARY")
    print(f"{'='*55}")
    print(f"  Start Capital     : ₹{INITIAL_CAPITAL:>12,.0f}")
    print(f"  Final Portfolio   : ₹{final_port:>12,.0f}")
    print(f"  Final Benchmark   : ₹{final_bench:>12,.0f}")
    print(f"  Gross P&L         : ₹{final_port - INITIAL_CAPITAL:>12,.0f}")
    print(f"{'='*55}")

    return results, holdings_log


if __name__ == "__main__":
    results, holdings_log = run_backtest()