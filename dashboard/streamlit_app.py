# dashboard/streamlit_app.py
# Interactive investor dashboard — run with: streamlit run dashboard/streamlit_app.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import sys, os
from datetime import datetime, timedelta
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.backtest import run_backtest
from src.metrics  import compute_all_metrics
from src.momentum import load_all_prices, compute_momentum_score, get_top20

# ── Page config ────────────────────────────────────────────────────
st.set_page_config(
    page_title = "Momentum Platform",
    page_icon  = "📈",
    layout     = "wide"
)

# ── Load data (cached so it doesn't re-run on every click) ─────────
@st.cache_data
def load_data():
    results, holdings_log = run_backtest()
    metrics               = compute_all_metrics(results)
    return results, holdings_log, metrics

@st.cache_data
def load_prices():
    return load_all_prices()

# ── Sidebar navigation ─────────────────────────────────────────────
st.sidebar.title("📈 Momentum Platform")
st.sidebar.markdown("NIFTY 100 | Risk-Adjusted Momentum")
st.sidebar.markdown("---")
page = st.sidebar.radio("Navigate", [
    "🏠 Overview",
    "📊 Performance",
    "📋 Holdings",
    "🔬 Statistics",
    "🔴 Live Portfolio"
])
st.sidebar.markdown("---")
st.sidebar.caption("Strategy: Top-20 Equal-Weight")
st.sidebar.caption("Rebalance: Quarterly")
st.sidebar.caption("Universe: NIFTY 100")
st.sidebar.caption("Capital: ₹10,00,000")
# ── Load everything ────────────────────────────────────────────────
with st.spinner("Loading backtest data..."):
    results, holdings_log, metrics = load_data()

s = metrics["strategy"]
b = metrics["benchmark"]
h = metrics["hypothesis_test"]

# ══════════════════════════════════════════════════════════════════
# PAGE 1 — OVERVIEW
# ══════════════════════════════════════════════════════════════════
if page == "🏠 Overview":
    st.title("📈 Momentum Portfolio — Overview")
    start_date = (datetime.today() - timedelta(days=3 * 365)).strftime("%b %Y")
    end_date   = datetime.today().strftime("%b %Y")
    st.markdown(f"**Strategy:** Risk-Adjusted Momentum | **Universe:** NIFTY 100 | **Period:** {start_date} – {end_date}")
    st.markdown("---")
    # ── KPI Cards ─────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Final Portfolio Value",
              f"₹{s['final_value']:,.0f}",
              f"+₹{s['final_value']-1_000_000:,.0f} from ₹10L")
    c2.metric("Strategy CAGR",
              f"{s['cagr']:.2%}",
              f"vs Benchmark {b['cagr']:.2%}")
    c3.metric("Sharpe Ratio",
              f"{s['sharpe']:.3f}",
              f"vs Benchmark {b['sharpe']:.3f}")
    c4.metric("Alpha (Excess CAGR)",
              f"{metrics['alpha']:.2%}")
    c5.metric("Max Drawdown",
              f"{s['max_drawdown']:.2%}",
              f"Benchmark {b['max_drawdown']:.2%}",
              delta_color="inverse")
    st.markdown("---")
    # ── Hypothesis test result banner ──────────────────────────────
    if h["reject_h0"]:
        st.success(f"✅ **Hypothesis Test: REJECT H0** — Strategy statistically outperforms the benchmark "
                   f"(p = {h['p_value_one']:.4f}, t = {h['t_statistic']:.3f})")
    else:
        st.warning(f"⚠️ **Hypothesis Test: FAIL TO REJECT H0** — No statistically significant outperformance "
                   f"(p = {h['p_value_one']:.4f})")

    # ── Mini cumulative chart ──────────────────────────────────────
    st.markdown("### Cumulative Portfolio Growth")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=results.index, y=results["portfolio_value"],
        name="Strategy", line=dict(color="#00C896", width=2)
    ))
    fig.add_trace(go.Scatter(
        x=results.index, y=results["benchmark_value"],
        name="NIFTY 100", line=dict(color="#636EFA", width=2, dash="dash")
    ))
    fig.add_hline(y=1_000_000, line_dash="dot", line_color="gray", annotation_text="Start ₹10L")
    fig.update_layout(
        height=350,
        xaxis_title="Date", yaxis_title="Portfolio Value (₹)",
        legend=dict(x=0.01, y=0.99),
        margin=dict(l=0, r=0, t=20, b=0)
    )
    st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════
# PAGE 2 — PERFORMANCE
# ══════════════════════════════════════════════════════════════════
elif page == "📊 Performance":
    st.title("📊 Performance Analysis")
    st.markdown("---")
    # ── Chart 1: Cumulative value ──────────────────────────────────
    st.markdown("### Portfolio vs Benchmark")
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=results.index, y=results["portfolio_value"],
        name="Strategy", line=dict(color="#00C896", width=2.5)
    ))
    fig1.add_trace(go.Scatter(
        x=results.index, y=results["benchmark_value"],
        name="NIFTY 100", line=dict(color="#636EFA", width=2, dash="dash")
    ))
    fig1.add_hline(y=1_000_000, line_dash="dot", line_color="gray")
    fig1.update_layout(height=400, xaxis_title="Date", yaxis_title="Value (₹)",
                       margin=dict(l=0,r=0,t=10,b=0))
    st.plotly_chart(fig1, use_container_width=True)
    col1, col2 = st.columns(2)

    # ── Chart 2: Drawdown ──────────────────────────────────────────
    with col1:
        st.markdown("### Drawdown Curve")
        rolling_max = results["portfolio_value"].cummax()
        drawdown    = (results["portfolio_value"] - rolling_max) / rolling_max * 100

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=results.index, y=drawdown,
            fill="tozeroy", name="Drawdown",
            line=dict(color="#EF553B"), fillcolor="rgba(239,85,59,0.3)"
        ))
        fig2.update_layout(height=300, xaxis_title="Date",
                           yaxis_title="Drawdown (%)",
                           margin=dict(l=0,r=0,t=10,b=0))
        st.plotly_chart(fig2, use_container_width=True)

    # ── Chart 3: Rolling volatility ────────────────────────────────
    with col2:
        st.markdown("### Rolling 30-Day Volatility")
        roll_vol = results["portfolio_return"].rolling(30).std() * np.sqrt(252) * 100

        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=results.index, y=roll_vol,
            name="Strategy Vol", line=dict(color="#FFA15A", width=2)
        ))
        fig3.update_layout(height=300, xaxis_title="Date",
                           yaxis_title="Annualized Volatility (%)",
                           margin=dict(l=0,r=0,t=10,b=0))
        st.plotly_chart(fig3, use_container_width=True)

    # ── Chart 4: Monthly return heatmap ───────────────────────────
    st.markdown("### Monthly Return Heatmap")
    monthly = results["portfolio_return"].resample("ME").apply(
        lambda x: (1 + x).prod() - 1
    ) * 100
    monthly_df         = monthly.reset_index()
    monthly_df.columns = ["date", "return"]
    monthly_df["year"] = monthly_df["date"].dt.year
    monthly_df["month"]= monthly_df["date"].dt.strftime("%b")
    pivot = monthly_df.pivot(index="year", columns="month", values="return")
    month_order = ["Jan","Feb","Mar","Apr","May","Jun",
                   "Jul","Aug","Sep","Oct","Nov","Dec"]
    pivot = pivot.reindex(columns=[m for m in month_order if m in pivot.columns])
    fig4 = px.imshow(
        pivot,
        color_continuous_scale="RdYlGn",
        color_continuous_midpoint=0,
        text_auto=".1f",
        aspect="auto"
    )
    fig4.update_layout(height=250, margin=dict(l=0,r=0,t=10,b=0))
    st.plotly_chart(fig4, use_container_width=True)

# ══════════════════════════════════════════════════════════════════
# PAGE 3 — HOLDINGS
# ══════════════════════════════════════════════════════════════════
elif page == "📋 Holdings":
    st.title("📋 Quarterly Holdings")
    st.markdown("---")
    if not holdings_log:
        st.warning("No holdings data available.")
    else:
        # Quarter selector
        quarters = [f"Q{i+1}: {h['rebalance_date']}" for i, h in enumerate(holdings_log)]
        selected = st.selectbox("Select Rebalance Quarter", quarters[::-1])
        idx      = len(quarters) - 1 - quarters[::-1].index(selected)
        entry    = holdings_log[idx]
        st.markdown(f"**Signal Date:** {entry['signal_date']}  |  "
                    f"**Execution Date:** {entry['rebalance_date']}")
        st.markdown("---")
        # Build holdings table
        rows = []
        for rank, ticker in enumerate(entry["holdings"], 1):
            score = entry["scores"].get(ticker, 0)
            rows.append({
                "Rank"           : rank,
                "Ticker"         : ticker,
                "Momentum Score" : round(score, 3),
                "Weight"         : "5.00%"
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        # Turnover between quarters
        if idx > 0:
            prev   = set(holdings_log[idx-1]["holdings"])
            curr   = set(entry["holdings"])
            added  = curr - prev
            removed= prev - curr
            st.markdown("---")
            col1, col2 = st.columns(2)
            col1.markdown(f"**➕ Added ({len(added)}):** {', '.join(sorted(added)) or 'None'}")
            col2.markdown(f"**➖ Removed ({len(removed)}):** {', '.join(sorted(removed)) or 'None'}")

# ══════════════════════════════════════════════════════════════════
# PAGE 4 — STATISTICS
# ══════════════════════════════════════════════════════════════════
elif page == "🔬 Statistics":
    st.title("🔬 Statistical Analysis")
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Full Metrics Comparison")
        comp = pd.DataFrame({
            "Metric"   : ["Final Value (₹)", "CAGR", "Sharpe Ratio",
                          "Max Drawdown", "Ann. Volatility", "Alpha"],
            "Strategy" : [f"₹{s['final_value']:,.0f}", f"{s['cagr']:.2%}",
                          f"{s['sharpe']:.3f}", f"{s['max_drawdown']:.2%}",
                          f"{s['volatility']:.2%}", f"{metrics['alpha']:.2%}"],
            "Benchmark": [f"₹{b['final_value']:,.0f}", f"{b['cagr']:.2%}",
                          f"{b['sharpe']:.3f}", f"{b['max_drawdown']:.2%}",
                          f"{b['volatility']:.2%}", "—"]
        })
        st.dataframe(comp, use_container_width=True, hide_index=True)
    with col2:
        st.markdown("### Hypothesis Test Results")
        hyp_data = pd.DataFrame({
            "Parameter": ["Observations", "Mean Monthly Excess",
                          "t-statistic", "p-value (one-tailed)",
                          "Cohen's d", "95% CI Lower", "95% CI Upper",
                          "Decision"],
            "Value"    : [
                h["n_observations"],
                f"{h['mean_excess']:.2%}",
                f"{h['t_statistic']:.3f}",
                f"{h['p_value_one']:.4f}",
                f"{h['cohens_d']:.3f}",
                f"{h['ci_95_low']:.2%}",
                f"{h['ci_95_high']:.2%}",
                "✅ Reject H0" if h["reject_h0"] else "❌ Fail to Reject H0"
            ]
        })
        st.dataframe(hyp_data, use_container_width=True, hide_index=True)
    # Monthly excess return distribution
    st.markdown("### Monthly Excess Return Distribution")
    port_m  = results["portfolio_return"].resample("ME").apply(lambda x: (1+x).prod()-1)
    bench_m = results["benchmark_return"].resample("ME").apply(lambda x: (1+x).prod()-1)
    excess  = (port_m - bench_m).dropna() * 100
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=excess, nbinsx=20, name="Monthly Excess Return",
                               marker_color="#00C896", opacity=0.75))
    fig.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="Zero")
    fig.add_vline(x=float(excess.mean()), line_dash="dot", line_color="green",
                  annotation_text=f"Mean: {excess.mean():.2f}%")
    fig.update_layout(height=350, xaxis_title="Monthly Excess Return (%)",
                      yaxis_title="Frequency", margin=dict(l=0,r=0,t=10,b=0))
    st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════
# PAGE 5 — LIVE PORTFOLIO
# ══════════════════════════════════════════════════════════════════
elif page == "🔴 Live Portfolio":
    st.title("🔴 Live Portfolio Signal")
    st.markdown("> ⚠️ This is a **simulated forward signal** based on latest available data. "
                "Not financial advice.")
    st.markdown("---")
    with st.spinner("Computing latest momentum scores..."):
        prices      = load_prices()
        latest_date = prices.index[-1]
        scores      = compute_momentum_score(prices, latest_date)
    if scores is not None:
        top20 = get_top20(scores)
        st.markdown(f"**Signal computed on:** {latest_date.date()}  |  "
                    f"**Stocks ranked:** {len(scores)}")
        rows = []
        for rank, (ticker, row) in enumerate(top20.iterrows(), 1):
            rows.append({
                "Rank"            : rank,
                "Ticker"          : ticker,
                "1Y Return"       : f"{row['r_252']:.2%}",
                "Ann. Volatility" : f"{row['sigma_annual']:.2%}",
                "Momentum Score"  : f"{row['score']:.3f}",
                "Weight"          : "5.00%"
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.markdown("---")
        st.markdown("**Equal allocation per stock:** ₹50,000 (5% of ₹10,00,000)")
    else:
        st.error("Could not compute live scores.")