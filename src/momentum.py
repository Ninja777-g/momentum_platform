# src/momentum.py
# Loads all ticker CSVs, computes momentum scores, and ranks stocks at each quarter-end

import pandas as pd
import numpy as np
import os

RAW_DIR = "data/raw"

def load_all_prices():
    all_series = {}
    for filename in os.listdir(RAW_DIR):
        if not filename.endswith(".csv"):
            continue
        ticker = filename.replace(".csv", "")
        if ticker == "^CNX100":
            continue
        filepath = os.path.join(RAW_DIR, filename)
        try:
            df = pd.read_csv(filepath, index_col=0, parse_dates=True)
            df.columns = ["close"]
            all_series[ticker] = df["close"]
        except Exception as e:
            print(f"  Could not load {ticker}: {e}")
    prices = pd.DataFrame(all_series)
    prices.sort_index(inplace=True)
    print(f"Loaded {prices.shape[1]} tickers, {prices.shape[0]} trading days")
    print(f"Date range: {prices.index[0].date()} to {prices.index[-1].date()}")
    return prices

def get_quarter_end_dates(prices, backtest_start="2023-01-01"):
    """
    Returns all quarter-end dates that fall within the backtest period.
    Quarter ends = last trading day of March, June, September, December.
    """
    # Filter to backtest period only
    backtest_prices = prices[prices.index >= backtest_start]
    # Get all dates in backtest period
    all_dates = backtest_prices.index
    quarter_ends = []
    for date in all_dates:
        month = date.month
        # Last trading day of Mar/Jun/Sep/Dec
        if month in [3, 6, 9, 12]:
            # Check if the NEXT date is in a different month (meaning this is the last day)
            next_dates = all_dates[all_dates > date]
            if len(next_dates) == 0:
                break
            if next_dates[0].month != month:
                quarter_ends.append(date)
    print(f"\nFound {len(quarter_ends)} quarter-end rebalance dates:")
    for d in quarter_ends:
        print(f"  {d.date()}")
    return quarter_ends

def compute_momentum_score(prices, signal_date, lookback=252):
    """
    For a given signal_date (quarter-end), computes momentum score
    for every ticker using the trailing 252 trading days.

    Momentum Score = R_252 / sigma_annual
    where:
        R_252       = (price_today - price_252_days_ago) / price_252_days_ago
        sigma_annual = std(daily_returns) * sqrt(252)
    """
    # Get all dates up to and including signal_date
    available = prices[prices.index <= signal_date]
    if len(available) < lookback:
        print(f"  Not enough data before {signal_date.date()}")
        return None
    # Take the last 252 rows = trailing 1 year
    window = available.tail(lookback)
    scores = {}
    for ticker in prices.columns:
        series = window[ticker].dropna()
        # Need full 252 days of data — skip if insufficient
        if len(series) < lookback * 0.9:   # allow up to 10% gaps
            continue
        # ── R_252: point-to-point return over the window ──────────
        price_start = series.iloc[0]
        price_end   = series.iloc[-1]
        if price_start <= 0:
            continue
        r_252 = (price_end - price_start) / price_start
        # ── Daily returns ──────────────────────────────────────────
        daily_returns = series.pct_change().dropna()
        # ── Annualized volatility ──────────────────────────────────
        sigma_annual = daily_returns.std() * np.sqrt(252)
        if sigma_annual == 0:
            continue
        # ── Momentum Score ─────────────────────────────────────────
        score = r_252 / sigma_annual
        scores[ticker] = {
            "r_252"       : round(r_252, 4),
            "sigma_annual": round(sigma_annual, 4),
            "score"       : round(score, 4)
        }
    # Convert to DataFrame and rank descending by score
    scores_df = pd.DataFrame(scores).T
    scores_df.index.name = "ticker"
    scores_df = scores_df.sort_values("score", ascending=False)
    return scores_df

def get_top20(scores_df):
    """Returns the top 20 stocks by momentum score."""
    return scores_df.head(20)

def run_momentum_check():
    """
    Test run — computes momentum scores at the first rebalance date
    and prints the Top 20.
    """
    print("=" * 55)
    print("MOMENTUM ENGINE — TEST RUN")
    print("=" * 55)
    # Step 1: Load all price data
    prices = load_all_prices()
    # Step 2: Get all quarter-end rebalance dates
    quarter_ends = get_quarter_end_dates(prices)
    if not quarter_ends:
        print("No quarter-end dates found — check your data.")
        return
    # Step 3: Compute scores at the FIRST rebalance date
    first_signal = quarter_ends[0]
    print(f"\nComputing momentum scores at: {first_signal.date()}")
    scores = compute_momentum_score(prices, first_signal)
    if scores is None:
        print("Could not compute scores.")
        return
    # Step 4: Show Top 20
    top20 = get_top20(scores)
    print(f"\nTop 20 Stocks by Momentum Score on {first_signal.date()}:")
    print("-" * 55)
    print(f"{'Rank':<6} {'Ticker':<20} {'R_252':>8} {'Volatility':>12} {'Score':>8}")
    print("-" * 55)
    for rank, (ticker, row) in enumerate(top20.iterrows(), 1):
        print(f"{rank:<6} {ticker:<20} {row['r_252']:>8.2%} {row['sigma_annual']:>12.2%} {row['score']:>8.3f}")
    print("-" * 55)
    print(f"\nTotal stocks ranked: {len(scores)}")
if __name__ == "__main__":
    run_momentum_check()