import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import streamlit.components.v1 as components
import calendar

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

INITIAL_INVESTMENT = 1000000.0
ANNUAL_BENCHMARK_RATE = 0.10
DAILY_BENCHMARK_RATE = ANNUAL_BENCHMARK_RATE / 252

# =====================
# 3. DATA LOADING
# =====================

@st.cache_data
def load_csv(filename: str) -> pd.DataFrame | None:
    if not os.path.exists(filename):
        return None
    try:
        df = pd.read_csv(filename)
        df.columns = df.columns.str.strip()
        
        # Date column detection
        date_candidates = ["Date", "Loop_Date", "Trade_Date", "date"]
        date_col = next((c for c in date_candidates if c in df.columns), None)
        
        if date_col:
            df = df.rename(columns={date_col: "Date"})
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df = df.dropna(subset=["Date"])
            return df.sort_values("Date").reset_index(drop=True)
        return None
    except:
        return None

# =====================
# 4. KPI & CHART LOGIC
# =====================

def calculate_kpis(df: pd.DataFrame):
    # Group PNL by date ensuring it stays as float cash
    df['PNL'] = pd.to_numeric(df['PNL'], errors='coerce').fillna(0)
    daily = df.groupby(df["Date"].dt.normalize())["PNL"].sum().reset_index()
    
    # Ensure Date is datetime for Plotly
    daily["Date"] = pd.to_datetime(daily["Date"])

    daily["Cumulative_PNL"] = daily["PNL"].cumsum()
    daily["NAV"] = INITIAL_INVESTMENT + daily["Cumulative_PNL"]

    # Calculate returns relative to the 1M investment
    daily["Strat_Cum_Ret"] = (daily["Cumulative_PNL"] / INITIAL_INVESTMENT) * 100
    
    # Benchmark indexing
    days = np.arange(1, len(daily) + 1)
    daily["Bench_Cum_Ret"] = ((1 + DAILY_BENCHMARK_RATE) ** days - 1) * 100

    # Monthly stats
    daily["YearMonth"] = daily["Date"].dt.to_period("M")
    monthly_pnl = daily.groupby("YearMonth")["PNL"].sum()
    
    total_ret = float(daily["Strat_Cum_Ret"].iloc[-1]) if not daily.empty else 0.0
    bench_ret = float(daily["Bench_Cum_Ret"].iloc[-1]) if not daily.empty else 0.0
    pct_bench = (total_ret / bench_ret * 100) if bench_ret != 0 else 0.0

    rolling_max = daily["NAV"].cummax()
    drawdown = (daily["NAV"] - rolling_max) / rolling_max * 100
    max_dd = float(drawdown.min()) if not drawdown.empty else 0.0

    return daily, total_ret, pct_bench, int((monthly_pnl > 0).sum()), int((monthly_pnl < 0).sum()), max_dd, (monthly_pnl.max() / INITIAL_INVESTMENT * 100), (monthly_pnl.min() / INITIAL_INVESTMENT * 100)

def build_prospectus_chart(daily_df: pd.DataFrame, strategy_name: str):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily_df["Date"], y=daily_df["Bench_Cum_Ret"],
        mode="lines", name="Benchmark (10% a.a.)",
        line=dict(color="#86868b", width=2, dash="dot"),
    ))
    fig.add_trace(go.Scatter(
        x=daily_df["Date"], y=daily_df["Strat_Cum_Ret"],
        mode="lines", name=strategy_name,
        line=dict(color="#0071e3", width=2.5),
        fill="tonexty", fillcolor="rgba(0, 113, 227, 0.08)",
        hovertemplate="<b>%{x|%b %d, %Y}</b><br>Return: %{y:.2f}%<extra></extra>",
    ))
    fig.update_layout(
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        margin=dict(l=0, r=0, t=10, b=0), height=420,
        hovermode="x unified", yaxis_title="Cumulative Return (%)",
        xaxis=dict(showgrid=False, linecolor="#d2d2d7"),
        yaxis=dict(showgrid=True, gridcolor="#f5f5f7", linecolor="#d2d2d7", ticksuffix="%"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig

def generate_monthly_matrix(daily_df: pd.DataFrame):
    df = daily_df.copy()
    df["Year"] = df["Date"].dt.year
    df["Month"] = df["Date"].dt.month
    
    pivot = (df.groupby(["Year", "Month"])["PNL"].sum() / INITIAL_INVESTMENT * 100).unstack()
    
    months = {i: calendar.month_name[i][:3] for i in range(1, 13)}
    pivot = pivot.rename(columns=months)
    
    for m in months.values():
        if m not in pivot.columns: pivot[m] = np.nan
            
    pivot = pivot[list(months.values())]
    pivot["YTD"] = pivot.sum(axis=1)
    return pivot.applymap(lambda x: f"{x:.2f}%" if pd.notnull(x) else "-")

# =====================
# 5. STRATEGY METADATA
# =====================

STRATEGIES = {
    "Olho Diário": {
        "file": "olho_logbook.csv",
        "type": "Intraday Quantitative Equity Portfolio",
        "audience": "Qualified Investors",
        "fee": "2.00% p.a. | 20% > Benchmark",
        "desc": "The Olho Diário strategy is a sophisticated intraday quantitative equity portfolio engineered to isolate and capitalize on immediate market momentum, gap imbalances, and structural price reversals.\n\nBy ensuring all positions are opened and closed within the same trading session, the portfolio maintains zero overnight exposure. This structural mandate acts as a powerful shield against macroeconomic shocks and unpredictable overnight gap risks."
    },
    "Quantitative Alpha - B3": {
        "file": "market_neutral_logbook.csv",
        "type": "Intraday Market-Neutral Statistical Arbitrage",
        "audience": "Professional Investors",
        "fee": "2.00% p.a. | 20% > Benchmark",
        "desc": "Quantitative Alpha - B3 is an institutional-grade, market-neutral statistical arbitrage framework engineered to exploit behavioral overreactions following the market open.\n\nUsing Volatility-Adjusted Z-Scores, the system identifies extreme panic or euphoria gaps and builds a balanced long/short book to capture intraday mean-reversion with zero market beta."
    },
    "LAM Strategy": {
        "file": "lam_strategy_logbook.csv",
        "type": "Auto-Adaptive Multi-Model Swing Portfolio",
        "audience": "Qualified Investors",
        "fee": "2.00% p.a. | 20% > Benchmark",
        "desc": "The flagship LAM Strategy is a highly advanced, auto-adaptive swing trading portfolio driven by a robust ensemble of seven distinct quantitative models.\n\nUtilizing the Hurst Exponent for regime detection and Ornstein-Uhlenbeck processes for half-life calculation, the strategy rotates capital across mean-reversion and volatility compression strategies."
    },
    "Swing Trade ATR": {
        "file": "swing_atr_logbook.csv",
        "type": "Systematic Scale-In Portfolio Matrix",
        "audience": "Qualified Investors",
        "fee": "1.50% p.a. | 20% > Benchmark",
        "desc": "The Swing Trade ATR framework is an institutional-grade, multi-tranche scale-in engine engineered to build positions during extreme pricing anomalies.\n\nGuarded by ATR volatility bands and regime filters, the strategy calculates precise scale-in levels to capture aggressive reversion alpha while strictly defining downside risk."
    },
}

# =====================
# 6. APP RENDER
# =====================

with st.sidebar:
    st.markdown("## LAM CAPITAL")
    st.markdown("<p style='color:#86868b; font-size: 0.9rem; margin-top:-10px;'>Quantitative Asset Management</p>", unsafe_allow_html=True)
    st.markdown("---")
    selected_strategy = st.radio("Select Portfolio Factsheet:", options=list(STRATEGIES.keys()))
    strat_meta = STRATEGIES[selected_strategy]
    st.markdown("---")
    st.markdown("<small style='color:#86868b;'>CONFIDENTIAL PROSPECTUS</small>", unsafe_allow_html=True)

raw_df = load_csv(strat_meta["file"])

if raw_df is None or "PNL" not in raw_df.columns:
    st.info(f"**System Notice:** Could not load valid data for `{selected_strategy}`. Check file: `{strat_meta['file']}`", icon="ℹ️")
    st.stop()

daily_df, total_ret, pct_bench, pos_m, neg_m, max_dd, max_m, min_m = calculate_kpis(raw_df)

# Header
col_t, col_a = st.columns([2.5, 1])
with col_t:
    st.markdown(f"<h1>{selected_strategy}</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='margin-top:-5px;'>{strat_meta['type']}</h3>", unsafe_allow_html=True)
with col_a:
    st.write("")
    st.download_button("⬇️ Export Ledger (.csv)", raw_df.to_csv(index=False).encode("utf-8"), strat_meta["file"], "text/csv", use_container_width=True)
    components.html('<button onclick="window.parent.print()" style="width: 100%; padding: 0.5rem; background-color: #1c3c54; color: white; border: none; border-radius: 4px; font-size: 1rem; cursor: pointer;">🖨️ Print to PDF</button>', height=50)

st.markdown("---")
for p in strat_meta["desc"].split("\n\n"):
    st.markdown(f"<p>{p}</p>", unsafe_allow_html=True)

# Performance
st.markdown("<h2>Cumulative Performance Evolution</h2>", unsafe_allow_html=True)
st.plotly_chart(build_prospectus_chart(daily_df, selected_strategy), use_container_width=True, config={"displayModeBar": False})

st.markdown("<h2>Monthly Return Matrix</h2>", unsafe_allow_html=True)
st.dataframe(generate_monthly_matrix(daily_df), use_container_width=True, hide_index=False)

# Metrics
col1, _, col2 = st.columns([1, 0.1, 1])
with col1:
    st.markdown("<h2>Risk & Performance Metrics</h2>", unsafe_allow_html=True)
    st.markdown(f"""<table class="info-table">
        <tr><th>Return Since Inception</th><td>{total_ret:.2f}%</td></tr>
        <tr><th>Return (% Benchmark)</th><td>{pct_bench:.2f}%</td></tr>
        <tr><th>Positive Months</th><td>{pos_m}</td></tr>
        <tr><th>Negative Months</th><td>{neg_m}</td></tr>
        <tr><th>Maximum Drawdown</th><td>{max_dd:.2f}%</td></tr>
        <tr><th>Best Monthly Return</th><td>{max_m:.2f}%</td></tr>
        <tr><th>Worst Monthly Return</th><td>{min_m:.2f}%</td></tr>
    </table>""", unsafe_allow_html=True)

with col2:
    st.markdown("<h2>General Information</h2>", unsafe_allow_html=True)
    start_date = daily_df["Date"].iloc[0].strftime("%B %d, %Y")
    st.markdown(f"""<table class="info-table">
        <tr><th>Inception Date</th><td>{start_date}</td></tr>
        <tr><th>Target Audience</th><td>{strat_meta['audience']}</td></tr>
        <tr><th>Fees</th><td>{strat_meta['fee']}</td></tr>
        <tr><th>Redemption Liquidity</th><td>T+30</td></tr>
        <tr><th>Minimum Allocation</th><td>$ 1,000,000</td></tr>
    </table>""", unsafe_allow_html=True)

st.markdown("---")
st.markdown("<p style='font-size:0.8rem; color:#86868b; text-align:center;'>This material is for informational purposes only. Past performance is not indicative of future results.</p>", unsafe_allow_html=True)
