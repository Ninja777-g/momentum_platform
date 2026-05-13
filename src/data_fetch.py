# src/data_fetch.py
# This file downloads 4 years of stock price data from Yahoo Finance

import yfinance as yf
import pandas as pd
import os
import time
from datetime import datetime, timedelta

# ── Where to save the downloaded data ──────────────────────────────
RAW_DIR       = "data/raw"
TICKER_FILE   = "data/tickers/nifty100_tickers.csv"
LOG_FILE      = "outputs/metrics/download_log.csv"

def get_date_range():
    """Returns start and end dates — 4 years back from today."""
    end_date   = datetime.today()
    start_date = end_date - timedelta(days=4 * 365 + 2)  # +2 for leap years
    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

def load_tickers():
    """Reads the nifty100_tickers.csv file and returns a list of tickers."""
    df = pd.read_csv(TICKER_FILE)
    tickers = df["ticker"].tolist()
    print(f"Loaded {len(tickers)} tickers from {TICKER_FILE}")
    return tickers

def download_batch(batch, start, end, attempt=1):
    """Downloads a batch of tickers from Yahoo Finance. Retries up to 3 times."""
    delays = [5, 15, 30]
    try:
        print(f"  Downloading batch: {batch} (attempt {attempt})")
        data = yf.download(
            batch,
            start=start,
            end=end,
            auto_adjust=True,   # gives adjusted prices automatically
            progress=False
        )
        return data
    except Exception as e:
        if attempt <= 3:
            wait = delays[attempt - 1]
            print(f"  Error: {e}. Waiting {wait}s before retry...")
            time.sleep(wait)
            return download_batch(batch, start, end, attempt + 1)
        else:
            print(f"  Failed after 3 attempts: {batch}")
            return None

def save_ticker_data(ticker, series):
    """Saves a single ticker's price series as a CSV file in data/raw/."""
    path = os.path.join(RAW_DIR, f"{ticker}.csv")
    series.to_csv(path, header=["close"])
    
def validate_ticker(ticker, series, min_rows=800):
    """Checks if a ticker has enough data rows."""
    if series is None or len(series) < min_rows:
        return False, len(series) if series is not None else 0
    return True, len(series)

def fetch_all():
    """Main function — downloads all NIFTY 100 tickers and saves them."""
    
    start, end = get_date_range()
    print(f"\nDate range: {start} to {end}")
    
    tickers = load_tickers()
    
    log_records = []   # will track success/failure for each ticker
    
    # ── Split tickers into batches of 20 ───────────────────────────
    batch_size = 20
    batches = [tickers[i:i+batch_size] for i in range(0, len(tickers), batch_size)]
    print(f"\nSplit into {len(batches)} batches of up to {batch_size} tickers each\n")
    
    for batch_num, batch in enumerate(batches, 1):
        print(f"--- Batch {batch_num}/{len(batches)} ---")
        
        raw_data = download_batch(batch, start, end)
        
        if raw_data is None:
            for ticker in batch:
                log_records.append({"ticker": ticker, "status": "FAILED", "rows": 0})
            continue
        
        # ── Extract each ticker's 'Close' column and save ──────────
        for ticker in batch:
            try:
                # When downloading multiple tickers, yfinance returns a MultiIndex
                if len(batch) == 1:
                    series = raw_data["Close"]
                else:
                    series = raw_data["Close"][ticker]
                
                # Drop NaN rows at the start/end
                series = series.dropna()
                
                # Validate
                is_valid, row_count = validate_ticker(ticker, series)
                
                if is_valid:
                    save_ticker_data(ticker, series)
                    log_records.append({"ticker": ticker, "status": "OK", "rows": row_count})
                    print(f"  ✓ {ticker}: {row_count} rows saved")
                else:
                    log_records.append({"ticker": ticker, "status": "INSUFFICIENT_DATA", "rows": row_count})
                    print(f"  ✗ {ticker}: only {row_count} rows — skipped")
                    
            except Exception as e:
                log_records.append({"ticker": ticker, "status": f"ERROR: {e}", "rows": 0})
                print(f"  ✗ {ticker}: error — {e}")
        
        # Small pause between batches to avoid rate limits
        if batch_num < len(batches):
            time.sleep(2)
    
    # ── Save the download log ───────────────────────────────────────
    log_df = pd.DataFrame(log_records)
    log_df.to_csv(LOG_FILE, index=False)
    
    ok_count   = len(log_df[log_df["status"] == "OK"])
    fail_count = len(log_df[log_df["status"] != "OK"])
    
    print(f"\n{'='*50}")
    print(f"Download complete!")
    print(f"  Successful : {ok_count} tickers")
    print(f"  Failed     : {fail_count} tickers")
    print(f"  Log saved  : {LOG_FILE}")
    print(f"{'='*50}\n")
    
    return log_df

# ── Run this file directly to trigger the download ─────────────────
if __name__ == "__main__":
    fetch_all()