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
        p { color: #515154; font-size: 1.05rem; line-height: 1.6; text-align: justify; white-space: pre-line; }
        .info-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 0.95rem; }
        .info-table th { text-align: left; padding: 10px 8px; border-bottom: 1px solid #e5e5ea; color: #86868b; font-weight: 500; width: 60%; }
        .info-table td { text-align: right; padding: 10px 8px; border-bottom: 1px solid #e5e5ea; color: #1d1d1f; font-weight: 600; }
        
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
        date_candidates = ["Date", "Loop_Date", "Trade_Date", "date"]
        date_col = next((c for c in date_candidates if c in df.columns), None)
        
        if date_col:
            df = df.rename(columns={date_col: "Date"})
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df = df.dropna(subset=["Date"])
            df['PNL'] = pd.to_numeric(df['PNL'], errors='coerce').fillna(0)
            return df.sort_values("Date").reset_index(drop=True)
        return None
    except:
        return None

# =====================
# 4. KPI & MATRIX LOGIC
# =====================

def calculate_kpis(df: pd.DataFrame):
    # Group PNL by normalized date
    daily = df.groupby(df["Date"].dt.normalize())["PNL"].sum().reset_index()
    daily["Date"] = pd.to_datetime(daily["Date"])
    daily["Cumulative_PNL"] = daily["PNL"].cumsum()
    daily["NAV"] = INITIAL_INVESTMENT + daily["Cumulative_PNL"]
    daily["Strat_Cum_Ret"] = (daily["Cumulative_PNL"] / INITIAL_INVESTMENT) * 100
    
    # Bench calc
    days_range = np.arange(1, len(daily) + 1)
    daily["Bench_Cum_Ret"] = ((1 + DAILY_BENCHMARK_RATE) ** days_range - 1) * 100
    
    daily["YearMonth"] = daily["Date"].dt.to_period("M")
    monthly_pnl = daily.groupby("YearMonth")["PNL"].sum()
    
    total_ret = float(daily["Strat_Cum_Ret"].iloc[-1]) if not daily.empty else 0.0
    bench_ret = float(daily["Bench_Cum_Ret"].iloc[-1]) if not daily.empty else 0.0
    pct_bench = (total_ret / bench_ret * 100) if bench_ret != 0 else 0.0
    
    rolling_max = daily["NAV"].cummax()
    drawdown = (daily["NAV"] - rolling_max) / rolling_max * 100
    max_dd = float(drawdown.min()) if not drawdown.empty else 0.0

    return daily, total_ret, pct_bench, int((monthly_pnl > 0).sum()), int((monthly_pnl < 0).sum()), max_dd, (monthly_pnl.max() / INITIAL_INVESTMENT * 100), (monthly_pnl.min() / INITIAL_INVESTMENT * 100)

def generate_monthly_matrix(daily_df: pd.DataFrame):
    df = daily_df.copy()
    df['Year'] = df['Date'].dt.year
    df['Month'] = df['Date'].dt.month
    
    pivot = (df.groupby(["Year", "Month"])["PNL"].sum() / INITIAL_INVESTMENT * 100).unstack()
    months_names = {i: calendar.month_name[i][:3] for i in range(1, 13)}
    pivot = pivot.rename(columns=months_names)
    
    for m in months_names.values():
        if m not in pivot.columns: pivot[m] = np.nan
            
    pivot = pivot[list(months_names.values())]
    pivot["YTD"] = pivot.sum(axis=1)
    
    # Format and return styled table
    return pivot.style.format("{:.2f}%", na_rep="-")

# =====================
# 5. STRATEGY METADATA
# =====================

STRATEGIES = {
    "Olho Diário": {
        "file": "olho_logbook.csv",
        "type": "Intraday Quantitative Equity Portfolio",
        "audience": "Qualified Investors",
        "fee": "2.00% p.a. | 20% > Benchmark",
        "desc": """The Olho Diário strategy is a sophisticated intraday quantitative equity portfolio engineered to isolate and capitalize on immediate market momentum, gap imbalances, and structural price reversals. At its core, this framework was developed to introduce high predictability into intraday trading by leveraging mathematical patterns established in preceding market sessions. Unlike traditional models that rely on static technical indicators, the Olho Diário engine dynamically develops a daily targeted portfolio consisting of the 20 highest-probability equities in the Brazilian market. To achieve this, the algorithm subjects each asset to a rigorous stress test, simulating over 2,000 unique scenarios daily. It continuously retrains its model using OHLC (Open, High, Low, Close) data and current-day opening auction values to identify forward-looking, highly profitable entry routes.

A defining characteristic of this strategy is its strict adherence to intraday execution. By ensuring that all positions are opened and closed within the same trading session, the portfolio maintains zero overnight exposure. This structural mandate acts as a powerful shield against macroeconomic shocks and unpredictable overnight gap risks. Furthermore, capital allocation is highly distributed across the selected assets, preventing concentration risk and ensuring that no single market cycle can fracture the strategy's foundation. Because the system is retrained daily, it possesses an exceptional capacity to pivot and adapt to shifting market regimes. This flexibility makes Olho Diário a versatile, adaptive solution for investors, providing consistent alpha generation and resilience in the face of high market volatility."""
    },
    "Quantitative Alpha - B3": {
        "file": "market_neutral_logbook.csv",
        "type": "Intraday Market-Neutral Statistical Arbitrage",
        "audience": "Professional Investors",
        "fee": "2.00% p.a. | 20% > Benchmark",
        "desc": """Quantitative Alpha - B3 is an institutional-grade, market-neutral statistical arbitrage strategy designed exclusively to exploit behavioral overreactions during the highly volatile market open. Moving away from traditional technical analysis or directional betting, this model relies entirely on Volatility-Adjusted Relative Extremes. The algorithm precisely isolates the overnight price action—the gap between the previous day's close and the current day's open—across the entire IBOV universe. It then divides this raw gap by each specific stock's 20-day historical standard deviation. This critical normalization process converts a simple percentage gap into a rigorous statistical Z-Score, allowing the engine to measure exactly how abnormal a morning gap is relative to that specific asset's historical behavioral baseline.

At exactly 10:00 AM, the algorithmic engine cross-sectionally ranks the analyzed universe based on these Z-Scores. It then constructs a perfectly balanced, market-neutral portfolio designed to act as a liquidity provider during early morning chaos. The system automatically executes long positions on the most severely suppressed gaps—fading morning retail panic—and simultaneously takes short positions on the most heavily inflated gaps, fading morning euphoria. By anchoring itself to both sides of the market evenly, the strategy entirely neutralizes broader market directional risk (Beta). The portfolio captures pure alpha through intraday mean-reversion as the targeted assets naturally gravitate back toward their fair value by the 4:00 PM market close. With strictly zero overnight exposure, Quantitative Alpha delivers a mathematically pure, non-directional return stream."""
    },
    "LAM Strategy": {
        "file": "lam_strategy_logbook.csv",
        "type": "Auto-Adaptive Multi-Model Swing Portfolio",
        "audience": "Qualified Investors",
        "fee": "2.00% p.a. | 20% > Benchmark",
        "desc": """The flagship LAM Strategy is a highly advanced, auto-adaptive swing trading portfolio driven by a robust ensemble of seven distinct quantitative models. Designed to navigate and conquer complex, multi-day market cycles, the foundation of this strategy rests heavily on rigorous statistical mathematics rather than conventional charting. The primary engine utilizes the Hurst Exponent to continuously monitor and detect shifting market regimes—accurately distinguishing between trending (persistent) and mean-reverting (anti-persistent) environments. Concurrently, it applies Ornstein-Uhlenbeck processes to calculate mathematically optimal mean-reversion half-lives, dictating exactly how long a swing position should be held.

Depending on the detected regime, the algorithmic framework dynamically rotates capital across its sub-strategies. These include models targeting extreme Volatility Compression (detecting quiet periods before explosive breakouts), Volume Climaxes (fading institutional exhaustion), adaptive Keltner Squeezes, and Anchored VWAP Divergences. Unlike our strictly intraday models, the LAM Strategy is designed to hold overnight exposure, capturing larger multi-day alpha. To mitigate the inherent risks of swing trading, the framework operates on a rigorous step-forward walking backtest architecture. Risk is managed asymmetrically via dynamic, volatility-adjusted Stop-Loss and Take-Profit brackets, alongside strict volume liquidity minimums to ensure seamless execution. Crucially, the engine features an institutional "Mirror Book" parameter. If macroeconomic headwinds dictate severe structural system decay, the algorithm can seamlessly invert its entire signal logic, allowing the portfolio to remain profitable even when traditional market conditions completely break down."""
    },
    "Swing Trade ATR": {
        "file": "swing_atr_logbook.csv",
        "type": "Systematic Scale-In Portfolio Matrix",
        "audience": "Qualified Investors",
        "fee": "1.50% p.a. | 20% > Benchmark",
        "desc": """The Swing Trade ATR framework is an institutional-grade, multi-tranche scale-in engine engineered to systematically build positions during extreme pricing anomalies. At its core, the strategy is predicated on the mathematical certainty of mean reversion, utilizing a 20-day Exponential Weighted Moving Average (EWMA) as the fundamental baseline for fair value. Rather than executing a single, rigid entry, the portfolio manager module deploys capital across five calculated tranches, scaling into positions as an asset deviates further from its baseline. 

To ensure mathematical precision, these scale-in levels are strictly guarded by Average True Range (ATR) volatility bands. As an asset drops 2.0, 3.0, 4.5, 6.0, and ultimately 8.0 ATR multiples below its EWMA, the engine progressively increases its capital allocation weighting. However, to prevent the system from blindly catching "falling knives" during structural market crashes, the strategy employs a rolling 60-day Hurst exponent as an absolute regime filter. If the Hurst calculation indicates a persistent downward trend (a value greater than 0.55), the scale-in logic is instantly aborted. The exit mechanism is equally systematic: the entire aggregate position is closed the moment the asset's price reverts to the rolling EWMA baseline. By combining dynamic volatility mapping, strict maximum gross exposure limits, and advanced regime detection, the Swing Trade ATR strategy offers a mathematically sound approach to capturing aggressive reversion alpha while strictly defining downside risk parameters."""
    },
}

# =====================
# 6. APP RENDER
# =====================

with st.sidebar:
    st.markdown("## LAM CAPITAL")
    st.markdown("<p style='color:#86868b; font-size: 0.9rem; margin-top:-10px;'>Quantitative Asset Management</p>", unsafe_allow_html=True)
    st.markdown("---")
    selected_strategy = st.radio("Select Strategy:", options=list(STRATEGIES.keys()))
    strat_meta = STRATEGIES[selected_strategy]

raw_df = load_csv(strat_meta["file"])

if raw_df is None:
    st.info(f"**System Notice:** File `{strat_meta['file']}` not found.", icon="ℹ️")
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
st.markdown(strat_meta["desc"])

# Chart
fig = go.Figure()
fig.add_trace(go.Scatter(x=daily_df["Date"], y=daily_df["Bench_Cum_Ret"], name="Benchmark", line=dict(color="#86868b", dash="dot")))
fig.add_trace(go.Scatter(x=daily_df["Date"], y=daily_df["Strat_Cum_Ret"], name=selected_strategy, line=dict(color="#0071e3", width=3), fill="tonexty", fillcolor="rgba(0, 113, 227, 0.08)"))
fig.update_layout(height=450, template="plotly_white", margin=dict(l=0,r=0,t=10,b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# Matrix
st.markdown("<h2>Monthly Return Matrix</h2>", unsafe_allow_html=True)
st.dataframe(generate_monthly_matrix(daily_df), use_container_width=True)

# Metrics
col1, _, col2 = st.columns([1, 0.1, 1])
with col1:
    st.markdown(f"""<h2>Risk & Performance Metrics</h2><table class="info-table">
        <tr><th>Return Since Inception</th><td>{total_ret:.2f}%</td></tr>
        <tr><th>Return (% Benchmark)</th><td>{pct_bench:.2f}%</td></tr>
        <tr><th>Positive Months</th><td>{pos_m}</td></tr>
        <tr><th>Maximum Drawdown</th><td>{max_dd:.2f}%</td></tr>
    </table>""", unsafe_allow_html=True)

with col2:
    st.markdown(f"""<h2>General Information</h2><table class="info-table">
        <tr><th>Inception Date</th><td>{daily_df["Date"].iloc[0].strftime("%B %d, %Y")}</td></tr>
        <tr><th>Fees</th><td>{strat_meta['fee']}</td></tr>
        <tr><th>Redemption Liquidity</th><td>T+30</td></tr>
        <tr><th>Minimum Allocation</th><td>$ 1,000,000</td></tr>
    </table>""", unsafe_allow_html=True)

st.markdown("---")
st.markdown("<p style='font-size:0.8rem; color:#86868b; text-align:center;'>This material is for informational purposes only. Past performance is not indicative of future results.</p>", unsafe_allow_html=True)
