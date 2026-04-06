import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import streamlit.components.v1 as components

# =====================
# 1. PAGE CONFIG & CSS
# =====================

st.set_page_config(
    page_title="LAM Capital | Factsheet",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        * { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
        .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1400px;}
        h1 { font-size: 2.2rem; color: #1d1d1f; margin-bottom: 0.2rem; font-weight: 700; letter-spacing: -0.02em;}
        h2 { font-size: 1.3rem; color: #1d1d1f; margin-top: 2rem; border-bottom: 1px solid #d2d2d7; padding-bottom: 0.3rem; font-weight: 600;}
        h3 { font-size: 1.1rem; color: #86868b; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; margin-bottom: 1rem; }
        p { color: #515154; font-size: 1.05rem; line-height: 1.6; text-align: justify; }
        .info-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 0.95rem; }
        .info-table th { text-align: left; padding: 10px 8px; border-bottom: 1px solid #e5e5ea; color: #86868b; font-weight: 500; width: 60%; }
        .info-table td { text-align: right; padding: 10px 8px; border-bottom: 1px solid #e5e5ea; color: #1d1d1f; font-weight: 600; }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        @media print {
            section[data-testid="stSidebar"] { display: none !important; }
            header[data-testid="stHeader"] { display: none !important; }
            .stDownloadButton, .print-btn-container { display: none !important; }
            .block-container { max-width: 100% !important; padding: 0 !important; }
            h1, h2, h3, p, td, th { color: #000 !important; }
            @page { margin: 1cm; size: A4 portrait; }
        }
    </style>
""", unsafe_allow_html=True)

# =====================
# 2. CONSTANTS
# =====================

INITIAL_INVESTMENT = 1_000_000.0
ANNUAL_BENCHMARK_RATE = 0.10
DAILY_BENCHMARK_RATE = ANNUAL_BENCHMARK_RATE / 252

# =====================
# 3. DATA LOADING
# =====================

@st.cache_data
def load_csv(filename: str) -> pd.DataFrame | None:
    """Load CSV from local filesystem and normalize date column."""
    if not os.path.exists(filename):
        return None

    df = pd.read_csv(filename)

    # Normalize column names
    df.columns = df.columns.str.strip()

    # Find date column
    date_candidates = ["Date", "Loop_Date", "Trade_Date", "date"]
    date_col = next((c for c in date_candidates if c in df.columns), None)
    if date_col is None:
        return None

    if date_col != "Date":
        df = df.rename(columns={date_col: "Date"})

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])

    return df.sort_values("Date").reset_index(drop=True)

# =====================
# 4. GENERIC PREPROCESSING (ALL STRATEGIES)
# =====================

def preprocess_all(df: pd.DataFrame) -> pd.DataFrame:
    """
    All strategies:
      - Assume PNL column already in cash (your Olho CSV is now converted).
    """
    df = df.copy()
    if "PNL" not in df.columns:
        return df
    df["PNL"] = pd.to_numeric(df["PNL"], errors="coerce")
    df = df.dropna(subset=["PNL"])
    return df

# =====================
# 5. KPI & CHART LOGIC
# =====================

def calculate_kpis(df: pd.DataFrame):
    # Aggregate by calendar date
    daily = df.groupby(df["Date"].dt.date)["PNL"].sum().reset_index()
    daily["Date"] = pd.to_datetime(daily["Date"])

    daily["Cumulative_PNL"] = daily["PNL"].cumsum()
    daily["NAV"] = INITIAL_INVESTMENT + daily["Cumulative_PNL"]

    daily["Strat_Cum_Ret"] = daily["Cumulative_PNL"] / INITIAL_INVESTMENT * 100
    daily["Bench_Cum_Ret"] = ((1 + DAILY_BENCHMARK_RATE) ** np.arange(1, len(daily) + 1) - 1) * 100

    daily["YearMonth"] = daily["Date"].dt.to_period("M")
    monthly_pnl = daily.groupby("YearMonth")["PNL"].sum()
    pos_months = int((monthly_pnl > 0).sum())
    neg_months = int((monthly_pnl < 0).sum())

    total_ret = float(daily["Strat_Cum_Ret"].iloc[-1]) if not daily.empty else 0.0
    bench_ret = float(daily["Bench_Cum_Ret"].iloc[-1]) if not daily.empty else 0.0
    pct_bench = (total_ret / bench_ret * 100) if bench_ret != 0 else 0.0

    rolling_max = daily["NAV"].cummax()
    drawdown = (daily["NAV"] - rolling_max) / rolling_max * 100
    max_dd = float(drawdown.min()) if not drawdown.empty else 0.0

    max_m_ret = (monthly_pnl.max() / INITIAL_INVESTMENT * 100) if not monthly_pnl.empty else 0.0
    min_m_ret = (monthly_pnl.min() / INITIAL_INVESTMENT * 100) if not monthly_pnl.empty else 0.0

    return daily, total_ret, pct_bench, pos_months, neg_months, max_dd, max_m_ret, min_m_ret


def build_prospectus_chart(daily_df: pd.DataFrame, strategy_name: str):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily_df["Date"],
        y=daily_df["Bench_Cum_Ret"],
        mode="lines",
        name="Benchmark (10% a.a.)",
        line=dict(color="#86868b", width=2, dash="dot"),
    ))
    fig.add_trace(go.Scatter(
        x=daily_df["Date"],
        y=daily_df["Strat_Cum_Ret"],
        mode="lines",
        name=strategy_name,
        line=dict(color="#0071e3", width=2.5),
        fill="tonexty",
        fillcolor="rgba(0, 113, 227, 0.08)",
        hovertemplate="<b>%{x|%b %d, %Y}</b><br>Return: %{y:.2f}%<extra></extra>",
    ))
    fig.update_layout(
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        margin=dict(l=0, r=0, t=10, b=0),
        height=420,
        hovermode="x unified",
        yaxis_title="Cumulative Return (%)",
        xaxis=dict(showgrid=False, linecolor="#d2d2d7"),
        yaxis=dict(showgrid=True, gridcolor="#f5f5f7", linecolor="#d2d2d7", ticksuffix="%"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def generate_monthly_matrix(daily_df: pd.DataFrame) -> pd.DataFrame:
    df = daily_df.copy()
    df["Year"] = df["Date"].dt.year
    df["Month"] = df["Date"].dt.month

    monthly_pnl = df.groupby(["Year", "Month"])["PNL"].sum()
    monthly_ret = monthly_pnl / INITIAL_INVESTMENT * 100
    pivot = monthly_ret.unstack()

    months_map = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
                  7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
    pivot = pivot.rename(columns=months_map)

    for m in months_map.values():
        if m not in pivot.columns:
            pivot[m] = np.nan

    pivot = pivot[list(months_map.values())]
    pivot["YTD"] = pivot.sum(axis=1)

    for col in pivot.columns:
        pivot[col] = pivot[col].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "-")

    return pivot.reset_index()

# =====================
# 6. STRATEGY METADATA
# =====================

STRATEGIES = {
    "Olho Diário": {
        "file": "olho_logbook.csv",
        "type": "Intraday Quantitative Equity Portfolio",
        "audience": "Qualified Investors",
        "fee": "2.00% p.a. | 20% > Benchmark",
        "desc": "The Olho Diário strategy is a sophisticated intraday quantitative equity portfolio..."
    },
    "Quantitative Alpha - B3": {
        "file": "market_neutral_logbook.csv",
        "type": "Intraday Market-Neutral Statistical Arbitrage",
        "audience": "Professional Investors",
        "fee": "2.00% p.a. | 20% > Benchmark",
        "desc": "Quantitative Alpha - B3 is an institutional-grade, market-neutral statistical arbitrage framework..."
    },
    "LAM Strategy": {
        "file": "lam_strategy_logbook.csv",
        "type": "Auto-Adaptive Multi-Model Swing Portfolio",
        "audience": "Qualified Investors",
        "fee": "2.00% p.a. | 20% > Benchmark",
        "desc": "The flagship LAM Strategy is a highly advanced, auto-adaptive swing trading portfolio..."
    },
    "Swing Trade ATR": {
        "file": "swing_atr_logbook.csv",
        "type": "Systematic Scale-In Portfolio Matrix",
        "audience": "Qualified Investors",
        "fee": "1.50% p.a. | 20% > Benchmark",
        "desc": "The Swing Trade ATR framework is an institutional-grade, multi-tranche scale-in engine..."
    },
}

# =====================
# 7. SIDEBAR
# =====================

with st.sidebar:
    st.markdown("## LAM CAPITAL")
    st.markdown(
        "<p style='color:#86868b; font-size: 0.9rem; margin-top:-10px;'>Quantitative Asset Management</p>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    selected_strategy = st.radio(
        "Select Portfolio Factsheet:", options=list(STRATEGIES.keys())
    )
    strat_meta = STRATEGIES[selected_strategy]
    expected_filename = strat_meta["file"]

    st.markdown("---")
    st.markdown(
        "<small style='color:#86868b;'>CONFIDENTIAL PROSPECTUS</small>",
        unsafe_allow_html=True,
    )

# =====================
# 8. LOAD & PREPROCESS
# =====================

raw_df = load_csv(expected_filename)

if raw_df is None or raw_df.empty:
    st.info(
        f"**System Notice:** Could not load data for `{selected_strategy}`. "
        f"Check that `{expected_filename}` exists and has a valid date column.",
        icon="ℹ️",
    )
    st.stop()

proc_df = preprocess_all(raw_df)

if proc_df is None or proc_df.empty:
    st.info(
        f"**System Notice:** After processing, there are no valid trades for `{selected_strategy}`. "
        "Please check the `PNL` column.",
        icon="ℹ️",
    )
    st.stop()

daily_df, total_ret, pct_bench, pos_months, neg_months, max_dd, max_m_ret, min_m_ret = calculate_kpis(proc_df)

# =====================
# 9. MAIN BODY
# =====================

col_title, col_actions = st.columns([2.5, 1])

with col_title:
    st.markdown(f"<h1>{selected_strategy}</h1>", unsafe_allow_html=True)
    st.markdown(
        f"<h3 style='margin-top:-5px;'>{strat_meta['type']}</h3>",
        unsafe_allow_html=True,
    )

with col_actions:
    st.write("")
    csv_bytes = proc_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Export Ledger (.csv)",
        data=csv_bytes,
        file_name=expected_filename,
        mime="text/csv",
        use_container_width=True,
    )
    components.html(
        """
        <button onclick="window.parent.print()" style="
            width: 100%; 
            padding: 0.5rem 1rem; 
            background-color: #1c3c54; 
            color: white; 
            border: none; 
            border-radius: 4px; 
            font-family: sans-serif; 
            font-size: 1rem; 
            cursor: pointer;
            transition: background-color 0.2s;">
            🖨️ Print to PDF
        </button>
        """,
        height=50,
    )

st.markdown("---")

# Strategy text
paragraphs = strat_meta["desc"].split("\\n\\n")
for p in paragraphs:
    st.markdown(f"<p>{p}</p>", unsafe_allow_html=True)

# Chart
st.markdown("<h2>Cumulative Performance Evolution</h2>", unsafe_allow_html=True)
chart = build_prospectus_chart(daily_df, selected_strategy)
st.plotly_chart(chart, use_container_width=True, config={"displayModeBar": False})

# Monthly matrix
st.markdown("<h2>Monthly Return Matrix</h2>", unsafe_allow_html=True)
matrix = generate_monthly_matrix(daily_df)
st.dataframe(matrix, use_container_width=True, hide_index=True)

# Metrics section
col1, _, col2 = st.columns([1, 0.1, 1])

with col1:
    st.markdown("<h2>Risk & Performance Metrics</h2>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <table class="info-table">
            <tr><th>Return Since Inception</th><td>{total_ret:.2f}%</td></tr>
            <tr><th>Return (% Benchmark)</th><td>{pct_bench:.2f}%</td></tr>
            <tr><th>Positive Months</th><td>{pos_months}</td></tr>
            <tr><th>Negative Months</th><td>{neg_months}</td></tr>
            <tr><th>Maximum Drawdown</th><td>{max_dd:.2f}%</td></tr>
            <tr><th>Best Monthly Return</th><td>{max_m_ret:.2f}%</td></tr>
            <tr><th>Worst Monthly Return</th><td>{min_m_ret:.2f}%</td></tr>
        </table>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown("<h2>General Information</h2>", unsafe_allow_html=True)
    start_date = (
        daily_df["Date"].iloc[0].strftime("%B %d, %Y") if not daily_df.empty else "N/A"
    )
    st.markdown(
        f"""
        <table class="info-table">
            <tr><th>Inception Date</th><td>{start_date}</td></tr>
            <tr><th>Target Audience</th><td>{strat_meta['audience']}</td></tr>
            <tr><th>Management & Perf. Fee</th><td>{strat_meta['fee']}</td></tr>
            <tr><th>Redemption Liquidity</th><td>T+30</td></tr>
            <tr><th>Minimum Allocation</th><td>$ 1,000,000</td></tr>
            <tr><th>Capital Mandate</th><td>Absolute Return</td></tr>
        </table>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")
st.markdown(
    "<p style='font-size:0.8rem; color:#86868b; text-align:center;'>"
    "This material is strictly for informational purposes and does not constitute an offer to sell or a solicitation to buy any securities. "
    "Past performance is not indicative of future results."
    "</p>",
    unsafe_allow_html=True,
)
