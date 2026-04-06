import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import re
import calendar
import streamlit.components.v1 as components

# ==========================================
# 1. PAGE CONFIGURATION & INSTITUTIONAL CSS
# ==========================================
st.set_page_config(
    page_title="LAM Capital | Factsheet",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        /* Base Typography & Layout */
        * { font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
        .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1400px; }
        h1 { font-size: 2.4rem; color: #111827; margin-bottom: 0.2rem; font-weight: 800; letter-spacing: -0.03em; }
        h2 { font-size: 1.25rem; color: #374151; margin-top: 2rem; border-bottom: 2px solid #e5e7eb; padding-bottom: 0.5rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }
        h3 { font-size: 1.15rem; color: #6b7280; font-weight: 500; margin-bottom: 1.5rem; letter-spacing: -0.01em; }
        p { color: #4b5563; font-size: 1.05rem; line-height: 1.7; text-align: justify; white-space: pre-line; }
        
        /* Metric Cards */
        .metric-grid { display: flex; gap: 15px; margin-bottom: 1.5rem; flex-wrap: wrap; }
        .metric-card { flex: 1; min-width: 150px; background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        .metric-title { font-size: 0.8rem; color: #6b7280; text-transform: uppercase; font-weight: 700; letter-spacing: 0.05em; margin-bottom: 5px; }
        .metric-value { font-size: 1.8rem; font-weight: 800; color: #111827; }
        .metric-sub { font-size: 0.85rem; font-weight: 600; margin-top: 4px; }
        .pos-val { color: #059669; }
        .neg-val { color: #dc2626; }
        
        /* Info Tables */
        .info-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 0.95rem; background: #fff; border-radius: 8px; overflow: hidden; border: 1px solid #e5e7eb; }
        .info-table th { text-align: left; padding: 12px 16px; border-bottom: 1px solid #e5e7eb; color: #6b7280; font-weight: 600; width: 50%; background: #f9fafb; }
        .info-table td { text-align: right; padding: 12px 16px; border-bottom: 1px solid #e5e7eb; color: #111827; font-weight: 700; }
        
        /* Hide Elements */
        #MainMenu, footer, header {visibility: hidden;}
        
        /* Print to PDF Formatting */
        @media print {
            section[data-testid="stSidebar"], .stDownloadButton, .print-btn { display: none !important; }
            .block-container { max-width: 100% !important; padding: 0 !important; }
            h1, h2, h3, p, td, th, .metric-value, .metric-title { color: #000 !important; }
            .metric-card, .info-table { box-shadow: none !important; border: 1px solid #ccc !important; }
            @page { margin: 1cm; size: A4 portrait; }
        }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONSTANTS & METADATA
# ==========================================
INITIAL_INVESTMENT = 1_000_000.0
ANNUAL_BENCHMARK_RATE = 0.10
DAILY_BENCHMARK_RATE = ANNUAL_BENCHMARK_RATE / 252
TRADING_DAYS_YEAR = 252

STRATEGIES = {
    "Olho Diário": {
        "file": "olho_logbook.csv",
        "type": "Intraday Quantitative Equity Portfolio",
        "audience": "Qualified Investors",
        "fee": "2.00% p.a. | 20% > Benchmark",
        "liq": "T+0 (Intraday)",
        "desc": """The Olho Diário strategy is a sophisticated intraday quantitative equity portfolio engineered to isolate and capitalize on immediate market momentum, gap imbalances, and structural price reversals. At its core, this framework was developed to introduce high predictability into intraday trading by leveraging mathematical patterns established in preceding market sessions. Unlike traditional models that rely on static technical indicators, the Olho Diário engine dynamically develops a daily targeted portfolio consisting of the 20 highest-probability equities in the Brazilian market. To achieve this, the algorithm subjects each asset to a rigorous stress test, simulating over 2,000 unique scenarios daily. It continuously retrains its model using OHLC data and current-day opening auction values to identify forward-looking, highly profitable entry routes.

A defining characteristic of this strategy is its strict adherence to intraday execution. By ensuring that all positions are opened and closed within the same trading session, the portfolio maintains zero overnight exposure. This structural mandate acts as a powerful shield against macroeconomic shocks and unpredictable overnight gap risks. Furthermore, capital allocation is highly distributed across the selected assets, preventing concentration risk and ensuring that no single market cycle can fracture the strategy's foundation. Because the system is retrained daily, it possesses an exceptional capacity to pivot and adapt to shifting market regimes."""
    },
    "Quantitative Alpha - B3": {
        "file": "market_neutral_logbook.csv",
        "type": "Intraday Market-Neutral Statistical Arbitrage",
        "audience": "Professional Investors",
        "fee": "2.00% p.a. | 20% > Benchmark",
        "liq": "T+0 (Intraday)",
        "desc": """Quantitative Alpha - B3 is an institutional-grade, market-neutral statistical arbitrage strategy designed exclusively to exploit behavioral overreactions during the highly volatile market open. Moving away from traditional technical analysis or directional betting, this model relies entirely on Volatility-Adjusted Relative Extremes. The algorithm precisely isolates the overnight price action—the gap between the previous day's close and the current day's open—across the entire IBOV universe. It then divides this raw gap by each specific stock's 20-day historical standard deviation. This critical normalization process converts a simple percentage gap into a rigorous statistical Z-Score, allowing the engine to measure exactly how abnormal a morning gap is relative to that specific asset's historical behavioral baseline.

At exactly 10:00 AM, the algorithmic engine cross-sectionally ranks the analyzed universe based on these Z-Scores. It then constructs a perfectly balanced, market-neutral portfolio designed to act as a liquidity provider during early morning chaos. The system automatically executes long positions on the most severely suppressed gaps—fading morning retail panic—and simultaneously takes short positions on the most heavily inflated gaps, fading morning euphoria. By anchoring itself to both sides of the market evenly, the strategy entirely neutralizes broader market directional risk (Beta). The portfolio captures pure alpha through intraday mean-reversion as the targeted assets naturally gravitate back toward their fair value by the 4:00 PM market close."""
    },
    "LAM Strategy": {
        "file": "lam_strategy_logbook.csv",
        "type": "Systematic Scale-In Portfolio Matrix",
        "audience": "Qualified Investors",
        "fee": "1.50% p.a. | 20% > Benchmark",
        "liq": "T+30",
        "desc": """The flagship LAM Strategy is an institutional-grade, multi-tranche scale-in engine engineered to systematically build positions during extreme pricing anomalies. At its core, the strategy is predicated on the mathematical certainty of mean reversion, utilizing a 20-day Exponential Weighted Moving Average (EWMA) as the fundamental baseline for fair value. Rather than executing a single, rigid entry, the portfolio manager module deploys capital across five calculated tranches, scaling into positions as an asset deviates further from its baseline. 

To ensure mathematical precision, these scale-in levels are strictly guarded by Average True Range (ATR) volatility bands. As an asset drops 2.0, 3.0, 4.5, 6.0, and ultimately 8.0 ATR multiples below its EWMA, the engine progressively increases its capital allocation weighting. However, to prevent the system from blindly catching "falling knives" during structural market crashes, the strategy employs a rolling 60-day Hurst exponent as an absolute regime filter. If the Hurst calculation indicates a persistent downward trend (a value greater than 0.55), the scale-in logic is instantly aborted. The exit mechanism is equally systematic: the entire aggregate position is closed the moment the asset's price reverts to the rolling EWMA baseline. By combining dynamic volatility mapping, strict maximum gross exposure limits, and advanced regime detection, the LAM Strategy offers a mathematically sound approach to capturing aggressive reversion alpha while strictly defining downside risk parameters."""
    },
    "Swing Trade": {
        "file": "swing_trade_logbook.csv",
        "type": "Auto-Adaptive Multi-Model Swing Portfolio",
        "audience": "Qualified Investors",
        "fee": "2.00% p.a. | 20% > Benchmark",
        "liq": "T+30",
        "desc": """The Swing Trade framework is a highly advanced, auto-adaptive portfolio driven by a robust ensemble of seven distinct quantitative models: Hurst_MR, OU_MR, Mom_Breakout, Vol_Climax, Vol_Compress, Keltner_Squeeze, and VWAP_Divergence. Designed to navigate and conquer complex, multi-day market cycles, the foundation of this strategy rests heavily on rigorous statistical mathematics. The primary engine utilizes the Hurst Exponent to continuously monitor and detect shifting market regimes—accurately distinguishing between trending (persistent) and mean-reverting (anti-persistent) environments.

Operating primarily (over 90% of the time) under the Ornstein-Uhlenbeck Mean Reversion (OU_MR) model, it calculates mathematically optimal half-lives to dictate exactly how long a swing position should be held. Depending on the detected regime, the framework dynamically rotates capital across its sub-strategies to capture explosive breakouts or fade institutional exhaustion. Unlike our strictly intraday models, this Swing Trade portfolio is designed to hold overnight exposure, capturing larger multi-day alpha. Risk is managed asymmetrically via dynamic, volatility-adjusted Stop-Loss and Take-Profit brackets, alongside strict volume liquidity minimums. Crucially, the engine features an institutional "Mirror Book" parameter, allowing the algorithm to seamlessly invert its entire signal logic if macroeconomic headwinds dictate severe structural system decay."""
    },
}

# ==========================================
# 3. BULLETPROOF DATA ENGINE
# ==========================================
def clean_currency(x):
    """Robust parser for messy PNL strings (handles R$, commas, dots, whitespace)"""
    if pd.isna(x): return 0.0
    if isinstance(x, (int, float)): return float(x)
    
    x = str(x).strip()
    # Handle Brazilian format (1.000,50 -> 1000.50) vs US format (1,000.50 -> 1000.50)
    if ',' in x and '.' in x:
        if x.rfind(',') > x.rfind('.'): # Comma is decimal
            x = x.replace('.', '').replace(',', '.')
        else: # Dot is decimal
            x = x.replace(',', '')
    elif ',' in x:
        x = x.replace(',', '.')
    
    # Strip everything except digits, minus sign, and period
    x = re.sub(r'[^\d\.-]', '', x)
    try:
        return float(x)
    except ValueError:
        return 0.0

@st.cache_data
def load_and_prepare_data(filename: str) -> pd.DataFrame | None:
    if not os.path.exists(filename): return None
    try:
        df = pd.read_csv(filename, sep=None, engine='python', encoding='utf-8-sig')
        df.columns = df.columns.str.strip()
        
        # 1. Map Date
        date_candidates = ["Date", "Loop_Date", "Trade_Date", "date", "Entry_Date", "Exit_Date"]
        date_col = next((c for c in date_candidates if c in df.columns), None)
        if not date_col: return None
        
        df = df.rename(columns={date_col: "Date"})
        df["Date"] = pd.to_datetime(df["Date"], dayfirst=False, errors="coerce")
        df = df.dropna(subset=["Date"])
        
        # 2. Map PNL
        pnl_candidates = ["PNL", "PnL", "PnL_R$", "pnl", "lucro", "Profit"]
        pnl_col = next((c for c in pnl_candidates if c in df.columns), None)
        if not pnl_col: return None
        
        df = df.rename(columns={pnl_col: "PNL"})
        df["PNL"] = df["PNL"].apply(clean_currency)
        
        return df.sort_values("Date").reset_index(drop=True)
    except Exception as e:
        st.error(f"Engine Error loading {filename}: {e}")
        return None

def process_kpis(df: pd.DataFrame):
    """Calculates Institutional Grade Time-Series KPIs"""
    # 1. Aggregate to Daily Timeline
    daily = df.groupby(df["Date"].dt.normalize())["PNL"].sum().reset_index()
    daily["Date"] = pd.to_datetime(daily["Date"])
    
    # 2. Ensure continuous timeline (fill missing days with 0 PNL)
    full_idx = pd.date_range(start=daily['Date'].min(), end=daily['Date'].max(), freq='B')
    daily = daily.set_index('Date').reindex(full_idx, fill_value=0.0).rename_axis('Date').reset_index()
    
    # 3. Core NAV Math
    daily["Cumulative_PNL"] = daily["PNL"].cumsum()
    daily["NAV"] = INITIAL_INVESTMENT + daily["Cumulative_PNL"]
    daily["Daily_Return"] = daily["NAV"].pct_change().fillna(0)
    daily["Strat_Cum_Ret"] = (daily["NAV"] / INITIAL_INVESTMENT - 1) * 100
    
    # 4. Benchmark Math
    days = np.arange(1, len(daily) + 1)
    daily["Bench_Cum_Ret"] = ((1 + DAILY_BENCHMARK_RATE) ** days - 1) * 100
    
    # 5. Advanced KPIs
    total_ret = daily["Strat_Cum_Ret"].iloc[-1]
    
    # Annualized Math
    trading_days = len(daily)
    years = trading_days / TRADING_DAYS_YEAR if trading_days > 0 else 1
    ann_ret = ((daily["NAV"].iloc[-1] / INITIAL_INVESTMENT) ** (1 / years) - 1) * 100
    ann_vol = daily["Daily_Return"].std() * np.sqrt(TRADING_DAYS_YEAR) * 100
    
    # Sharpe Ratio (Risk Free Rate approx 10%)
    rf_daily = ANNUAL_BENCHMARK_RATE / TRADING_DAYS_YEAR
    excess_returns = daily["Daily_Return"] - rf_daily
    sharpe = (excess_returns.mean() / daily["Daily_Return"].std()) * np.sqrt(TRADING_DAYS_YEAR) if daily["Daily_Return"].std() > 0 else 0
    
    # Drawdown
    rolling_max = daily["NAV"].cummax()
    daily["Drawdown"] = ((daily["NAV"] - rolling_max) / rolling_max) * 100
    max_dd = daily["Drawdown"].min()
    
    # Win Rate (Days)
    win_rate = (len(daily[daily["PNL"] > 0]) / len(daily[daily["PNL"] != 0])) * 100 if len(daily[daily["PNL"] != 0]) > 0 else 0

    return daily, total_ret, ann_ret, ann_vol, sharpe, max_dd, win_rate

# ==========================================
# 4. ADVANCED PLOTLY CHARTS
# ==========================================
def plot_master_evolution(daily: pd.DataFrame, strat_name: str):
    """Creates a 2-panel Plotly chart (NAV Curve + Underwater Drawdown)"""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.75, 0.25])
    
    # Top Panel: NAV
    fig.add_trace(go.Scatter(x=daily["Date"], y=daily["Bench_Cum_Ret"], name="Benchmark (10% a.a.)", line=dict(color="#9ca3af", width=2, dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=daily["Date"], y=daily["Strat_Cum_Ret"], name=strat_name, line=dict(color="#2563eb", width=2.5), fill="tonexty", fillcolor="rgba(37, 99, 235, 0.08)"), row=1, col=1)
    
    # Bottom Panel: Drawdown
    fig.add_trace(go.Scatter(x=daily["Date"], y=daily["Drawdown"], name="Drawdown", line=dict(color="#dc2626", width=1), fill="tozeroy", fillcolor="rgba(220, 38, 38, 0.2)"), row=2, col=1)
    
    fig.update_layout(
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff", height=550, margin=dict(l=0, r=0, t=20, b=0),
        hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        showlegend=True
    )
    fig.update_xaxes(showgrid=False, linecolor="#d1d5db")
    fig.update_yaxes(title_text="Cumulative Return (%)", ticksuffix="%", showgrid=True, gridcolor="#f3f4f6", row=1, col=1)
    fig.update_yaxes(title_text="Drawdown (%)", ticksuffix="%", showgrid=True, gridcolor="#f3f4f6", row=2, col=1)
    return fig

def plot_monthly_heatmap(daily: pd.DataFrame):
    """Creates a beautiful Plotly Heatmap instead of Pandas Styler"""
    df = daily.copy()
    df['Year'] = df['Date'].dt.year
    df['Month'] = df['Date'].dt.month
    
    pivot = (df.groupby(["Year", "Month"])["PNL"].sum() / INITIAL_INVESTMENT * 100).unstack()
    months_str = [calendar.month_name[i][:3] for i in range(1, 13)]
    
    # Ensure all 12 months exist
    for i, m in enumerate(months_str):
        if (i+1) not in pivot.columns: pivot[i+1] = np.nan
    
    pivot = pivot[range(1, 13)]
    pivot.columns = months_str
    pivot["YTD"] = pivot.sum(axis=1)
    
    # Prepare data for Plotly
    z_data = pivot.values
    y_data = pivot.index.astype(str).tolist()
    x_data = months_str + ["YTD"]
    
    # Text annotations
    text_data = [[f"{val:.2f}%" if not np.isnan(val) else "" for val in row] for row in z_data]
    
    fig = go.Figure(data=go.Heatmap(
        z=z_data, x=x_data, y=y_data, text=text_data, texttemplate="%{text}",
        colorscale="RdYlGn", zmid=0, showscale=False, xgap=3, ygap=3,
        hoverinfo="skip"
    ))
    
    fig.update_layout(
        height=50 + (len(y_data) * 40), margin=dict(l=0, r=0, t=10, b=0),
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        xaxis=dict(side="top", fixedrange=True), yaxis=dict(autorange="reversed", fixedrange=True)
    )
    return fig

def plot_distribution(daily: pd.DataFrame):
    """Histogram of daily returns"""
    returns = daily[daily["Daily_Return"] != 0]["Daily_Return"] * 100
    fig = go.Figure(data=[go.Histogram(x=returns, nbinsx=50, marker_color="#3b82f6", opacity=0.8)])
    fig.update_layout(
        height=300, margin=dict(l=0, r=0, t=10, b=0),
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        xaxis_title="Daily Return (%)", yaxis_title="Frequency",
        xaxis=dict(showgrid=True, gridcolor="#f3f4f6", ticksuffix="%"),
        yaxis=dict(showgrid=True, gridcolor="#f3f4f6"),
        bargap=0.05
    )
    return fig

# ==========================================
# 5. RENDER ENGINE (UI)
# ==========================================
with st.sidebar:
    st.markdown("## LAM CAPITAL")
    st.markdown("<p style='color:#6b7280; font-size: 0.9rem; margin-top:-10px; font-weight: 500;'>Quantitative Asset Management</p>", unsafe_allow_html=True)
    st.markdown("---")
    selected_strategy = st.radio("Select Strategy Factsheet:", options=list(STRATEGIES.keys()))
    strat_meta = STRATEGIES[selected_strategy]

# Data Loading
raw_df = load_and_prepare_data(strat_meta["file"])
if raw_df is None or raw_df.empty:
    st.info(f"**System Notice:** Expected file `{strat_meta['file']}` not found or invalid format. Please sync the data lake.", icon="ℹ️")
    st.stop()

# Compute Math
daily_df, tot_ret, ann_ret, ann_vol, sharpe, max_dd, win_rate = process_kpis(raw_df)

# Header
col_t, col_a = st.columns([3, 1])
with col_t:
    st.markdown(f"<h1>{selected_strategy}</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='margin-top:-5px;'>{strat_meta['type']}</h3>", unsafe_allow_html=True)
with col_a:
    st.write("")
    csv_bytes = raw_df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Export Execution Ledger", csv_bytes, strat_meta["file"], "text/csv", use_container_width=True)
    components.html("""
        <button class="print-btn" onclick="window.parent.print()" style="
            width: 100%; padding: 0.6rem; background-color: #111827; color: white; border: none; 
            border-radius: 6px; font-size: 0.95rem; font-weight: 600; cursor: pointer; transition: 0.2s;">
            🖨️ Print Factsheet (PDF)
        </button>
    """, height=50)

# Top Metric Cards (Custom HTML)
st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-card">
            <div class="metric-title">Total Return</div>
            <div class="metric-value {'pos-val' if tot_ret > 0 else 'neg-val'}">{tot_ret:.2f}%</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Ann. Return</div>
            <div class="metric-value {'pos-val' if ann_ret > 0 else 'neg-val'}">{ann_ret:.2f}%</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Sharpe Ratio</div>
            <div class="metric-value">{sharpe:.2f}</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Max Drawdown</div>
            <div class="metric-value neg-val">{max_dd:.2f}%</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Daily Win Rate</div>
            <div class="metric-value">{win_rate:.1f}%</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# Main Content
st.markdown(strat_meta["desc"])

st.markdown("<h2>Cumulative Performance Evolution</h2>", unsafe_allow_html=True)
st.plotly_chart(plot_master_evolution(daily_df, selected_strategy), use_container_width=True, config={"displayModeBar": False})

# Bottom Layout: Heatmap + Distribution
col_hm, col_dist = st.columns([1.5, 1])
with col_hm:
    st.markdown("<h2>Monthly Return Matrix</h2>", unsafe_allow_html=True)
    st.plotly_chart(plot_monthly_heatmap(daily_df), use_container_width=True, config={"displayModeBar": False})

with col_dist:
    st.markdown("<h2>Daily Return Distribution</h2>", unsafe_allow_html=True)
    st.plotly_chart(plot_distribution(daily_df), use_container_width=True, config={"displayModeBar": False})

# Info Tables
c1, _, c2 = st.columns([1, 0.05, 1])
with c1:
    st.markdown("<h2>Risk Analytics</h2>", unsafe_allow_html=True)
    st.markdown(f"""<table class="info-table">
        <tr><th>Annualized Volatility</th><td>{ann_vol:.2f}%</td></tr>
        <tr><th>Risk-Free Rate (Assumption)</th><td>{ANNUAL_BENCHMARK_RATE*100:.1f}% a.a.</td></tr>
        <tr><th>Worst Drawdown</th><td class="neg-val">{max_dd:.2f}%</td></tr>
        <tr><th>Trading Days Active</th><td>{len(daily_df[daily_df["Daily_Return"] != 0])}</td></tr>
    </table>""", unsafe_allow_html=True)

with c2:
    st.markdown("<h2>Fund Information</h2>", unsafe_allow_html=True)
    st.markdown(f"""<table class="info-table">
        <tr><th>Inception Date</th><td>{daily_df["Date"].iloc[0].strftime("%B %d, %Y")}</td></tr>
        <tr><th>Target Audience</th><td>{strat_meta['audience']}</td></tr>
        <tr><th>Management & Perf. Fee</th><td>{strat_meta['fee']}</td></tr>
        <tr><th>Redemption Liquidity</th><td>{strat_meta['liq']}</td></tr>
    </table>""", unsafe_allow_html=True)

st.markdown("---")
st.markdown("<p style='font-size:0.8rem; color:#9ca3af; text-align:center;'>Confidential Prospectus. This material is for informational purposes only and does not constitute an offer to sell or a solicitation to buy any securities. Past performance is not indicative of future results.</p>", unsafe_allow_html=True)
