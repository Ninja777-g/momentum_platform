# src/metrics.py
# Computes all performance metrics: CAGR, Sharpe, Max Drawdown, Alpha, t-test

import pandas as pd
import numpy as np
from scipy import stats

RISK_FREE_RATE = 0.06   # 6% annual — approximate Indian T-bill rate
TRADING_DAYS   = 252

def compute_cagr(start_value, end_value, years):
    """Compound Annual Growth Rate."""
    return (end_value / start_value) ** (1 / years) - 1

def compute_sharpe(daily_returns, risk_free_rate=RISK_FREE_RATE):
    """Annualized Sharpe Ratio using daily excess returns."""
    daily_rf      = risk_free_rate / TRADING_DAYS
    excess        = daily_returns - daily_rf
    if excess.std() == 0:
        return 0
    return (excess.mean() / excess.std()) * np.sqrt(TRADING_DAYS)

def compute_max_drawdown(values):
    """Worst peak-to-trough decline in the value curve."""
    rolling_max = values.cummax()
    drawdown    = (values - rolling_max) / rolling_max
    return drawdown.min()   # most negative value

def compute_monthly_returns(daily_values):
    """Resamples daily NAV to monthly returns."""
    monthly = daily_values.resample("ME").last()
    return monthly.pct_change().dropna()

def run_hypothesis_test(strategy_monthly, benchmark_monthly):
    """
    Paired t-test on monthly excess returns.
    H0: mean excess return = 0
    H1: mean excess return > 0 (strategy outperforms)
    """
    # Align both series to same dates
    combined        = pd.DataFrame({
        "strategy" : strategy_monthly,
        "benchmark": benchmark_monthly
    }).dropna()
    excess          = combined["strategy"] - combined["benchmark"]
    t_stat, p_value = stats.ttest_rel(combined["strategy"], combined["benchmark"])
    # One-tailed p-value (we care only about outperformance)
    p_one_tailed    = p_value / 2
    # Effect size (Cohen's d)
    cohens_d        = excess.mean() / excess.std()
    # 95% confidence interval on mean excess return
    ci              = stats.t.interval(
                        0.95,
                        df=len(excess)-1,
                        loc=excess.mean(),
                        scale=stats.sem(excess)
                      )
    return {
        "n_observations"  : len(excess),
        "mean_excess"     : excess.mean(),
        "t_statistic"     : t_stat,
        "p_value_two"     : p_value,
        "p_value_one"     : p_one_tailed,
        "reject_h0"       : p_one_tailed < 0.05,
        "cohens_d"        : cohens_d,
        "ci_95_low"       : ci[0],
        "ci_95_high"      : ci[1]
    }

def compute_all_metrics(results):
    """
    Takes the backtest results DataFrame and computes all metrics.
    results must have columns: portfolio_value, benchmark_value
    """
    port  = results["portfolio_value"].dropna()
    bench = results["benchmark_value"].dropna()
    # Number of years
    years = len(port) / TRADING_DAYS
    # ── CAGR ───────────────────────────────────────────────────────
    port_cagr  = compute_cagr(port.iloc[0],  port.iloc[-1],  years)
    bench_cagr = compute_cagr(bench.iloc[0], bench.iloc[-1], years)
    # ── Sharpe ─────────────────────────────────────────────────────
    port_returns  = results["portfolio_return"].dropna()
    bench_returns = results["benchmark_return"].dropna()
    port_sharpe  = compute_sharpe(port_returns)
    bench_sharpe = compute_sharpe(bench_returns)
    # ── Max Drawdown ───────────────────────────────────────────────
    port_mdd  = compute_max_drawdown(port)
    bench_mdd = compute_max_drawdown(bench)
    # ── Alpha ──────────────────────────────────────────────────────
    alpha = port_cagr - bench_cagr
    # ── Volatility ─────────────────────────────────────────────────
    port_vol  = port_returns.std()  * np.sqrt(TRADING_DAYS)
    bench_vol = bench_returns.std() * np.sqrt(TRADING_DAYS)
    # ── Hypothesis Test ────────────────────────────────────────────
    port_monthly  = compute_monthly_returns(port)
    bench_monthly = compute_monthly_returns(bench)
    hyp           = run_hypothesis_test(port_monthly, bench_monthly)
    # ── Package everything ─────────────────────────────────────────
    metrics = {
        "strategy": {
            "final_value"  : port.iloc[-1],
            "cagr"         : port_cagr,
            "sharpe"       : port_sharpe,
            "max_drawdown" : port_mdd,
            "volatility"   : port_vol,
        },
        "benchmark": {
            "final_value"  : bench.iloc[-1],
            "cagr"         : bench_cagr,
            "sharpe"       : bench_sharpe,
            "max_drawdown" : bench_mdd,
            "volatility"   : bench_vol,
        },
        "alpha"           : alpha,
        "hypothesis_test" : hyp
    }
    return metrics

def print_metrics(metrics):
    """Prints a formatted metrics report."""
    s  = metrics["strategy"]
    b  = metrics["benchmark"]
    h  = metrics["hypothesis_test"]
    print(f"\n{'='*55}")
    print(f"  PERFORMANCE METRICS REPORT")
    print(f"{'='*55}")
    print(f"  {'Metric':<22} {'Strategy':>12} {'Benchmark':>12}")
    print(f"  {'-'*46}")
    print(f"  {'Final Value (₹)':<22} {s['final_value']:>12,.0f} {b['final_value']:>12,.0f}")
    print(f"  {'CAGR':<22} {s['cagr']:>12.2%} {b['cagr']:>12.2%}")
    print(f"  {'Sharpe Ratio':<22} {s['sharpe']:>12.3f} {b['sharpe']:>12.3f}")
    print(f"  {'Max Drawdown':<22} {s['max_drawdown']:>12.2%} {b['max_drawdown']:>12.2%}")
    print(f"  {'Ann. Volatility':<22} {s['volatility']:>12.2%} {b['volatility']:>12.2%}")
    print(f"  {'-'*46}")
    print(f"  {'Alpha (excess CAGR)':<22} {metrics['alpha']:>12.2%}")
    print(f"\n  HYPOTHESIS TEST (Paired t-test)")
    print(f"  {'-'*46}")
    print(f"  {'Observations':<22} {h['n_observations']:>12}")
    print(f"  {'Mean Monthly Excess':<22} {h['mean_excess']:>12.2%}")
    print(f"  {'t-statistic':<22} {h['t_statistic']:>12.3f}")
    print(f"  {'p-value (one-tailed)':<22} {h['p_value_one']:>12.4f}")
    print(f"  {'Cohens_d':<22} {h['cohens_d']:>12.3f}")
    print(f"  {'95% CI':<22} [{h['ci_95_low']:>6.2%}, {h['ci_95_high']:>6.2%}]")
    print(f"  {'-'*46}")
    if h["reject_h0"]:
        print(f"  RESULT: REJECT H0 ✅ Strategy significantly outperforms!")
    else:
        print(f"  RESULT: FAIL TO REJECT H0 ❌ No significant outperformance")
    print(f"{'='*55}\n")
if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from src.backtest import run_backtest
    results, _ = run_backtest()
    metrics    = compute_all_metrics(results)
    print_metrics(metrics)