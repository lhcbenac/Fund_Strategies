import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import calendar
import os

# --- 1. PAGE CONFIGURATION & STYLING ---
st.set_page_config(
    page_title="LAM Capital | Factsheet",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        * { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
        .block-container { padding-top: 2rem; padding-bottom: 3rem; }
        h1 { font-size: 2.2rem; color: #1d1d1f; margin-bottom: 0.2rem; font-weight: 700; }
        h2 { font-size: 1.3rem; color: #1d1d1f; margin-top: 2rem; border-bottom: 1px solid #d2d2d7; padding-bottom: 0.3rem; font-weight: 600;}
        h3 { font-size: 1.1rem; color: #86868b; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; margin-bottom: 1rem; }
        p { color: #515154; font-size: 1.05rem; line-height: 1.6; text-align: justify; }
        .info-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 0.95rem; }
        .info-table th { text-align: left; padding: 8px; border-bottom: 1px solid #e5e5ea; color: #86868b; font-weight: 500; width: 60%; }
        .info-table td { text-align: right; padding: 8px; border-bottom: 1px solid #e5e5ea; color: #1d1d1f; font-weight: 600; }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 2. GLOBAL CONSTANTS ---
INITIAL_INVESTMENT = 1000000.0  
ANNUAL_BENCHMARK_RATE = 0.10 # 10% Annual Benchmark (CDI Equivalent)
DAILY_BENCHMARK_RATE = ANNUAL_BENCHMARK_RATE / 252

# --- 3. CORE LOGIC & METRICS ---
@st.cache_data
def load_and_clean_data(filename: str, uploaded_file=None):
    try:
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
        elif os.path.exists(filename):
            df = pd.read_csv(filename)
        else:
            return None
        df['Date'] = pd.to_datetime(df['Date'])
        return df.sort_values('Date').reset_index(drop=True)
    except Exception as e:
        st.error(f"Error reading data: {e}")
        return None

def calculate_kpis(df: pd.DataFrame):
    daily = df.groupby(df['Date'].dt.date)['PNL'].sum().reset_index()
    daily['Date'] = pd.to_datetime(daily['Date'])
    
    daily['Cumulative_PNL'] = daily['PNL'].cumsum()
    daily['NAV'] = INITIAL_INVESTMENT + daily['Cumulative_PNL']
    
    # Cumulative Percentage Return (for charting)
    daily['Strat_Cum_Ret'] = (daily['Cumulative_PNL'] / INITIAL_INVESTMENT) * 100
    daily['Bench_Cum_Ret'] = ((1 + DAILY_BENCHMARK_RATE) ** np.arange(1, len(daily) + 1) - 1) * 100
    
    # Monthly Data for Hit Rate
    daily['YearMonth'] = daily['Date'].dt.to_period('M')
    monthly_returns = daily.groupby('YearMonth')['PNL'].sum()
    positive_months = (monthly_returns > 0).sum()
    negative_months = (monthly_returns < 0).sum()
    
    # Advanced Metrics
    total_ret = daily['Strat_Cum_Ret'].iloc[-1] if not daily.empty else 0
    bench_ret = daily['Bench_Cum_Ret'].iloc[-1] if not daily.empty else 0
    pct_of_benchmark = (total_ret / bench_ret) * 100 if bench_ret != 0 else 0
    
    rolling_max = daily['NAV'].cummax()
    drawdown = ((daily['NAV'] - rolling_max) / rolling_max) * 100
    max_drawdown = drawdown.min()
    
    max_month_ret = (monthly_returns.max() / INITIAL_INVESTMENT) * 100 if not monthly_returns.empty else 0
    min_month_ret = (monthly_returns.min() / INITIAL_INVESTMENT) * 100 if not monthly_returns.empty else 0

    return daily, total_ret, pct_of_benchmark, positive_months, negative_months, max_drawdown, max_month_ret, min_month_ret

def build_prospectus_chart(daily_df: pd.DataFrame, strategy_name: str):
    fig = go.Figure()
    
    # Benchmark Curve
    fig.add_trace(go.Scatter(
        x=daily_df['Date'], y=daily_df['Bench_Cum_Ret'],
        mode='lines', name='Benchmark (CDI Proxy)',
        line=dict(color='#1c3c54', width=2)
    ))

    # Strategy Curve
    fig.add_trace(go.Scatter(
        x=daily_df['Date'], y=daily_df['Strat_Cum_Ret'],
        mode='lines', name=strategy_name,
        line=dict(color='#0088cc', width=2), 
        fill='tonexty', fillcolor='rgba(0, 136, 204, 0.1)',
        hovertemplate="<b>%{x|%b %d, %Y}</b><br>Return: %{y:.2f}%<extra></extra>"
    ))

    fig.update_layout(
        plot_bgcolor='#ffffff', paper_bgcolor='#ffffff',
        margin=dict(l=0, r=0, t=10, b=0),
        height=400, hovermode='x unified',
        yaxis_title="Cumulative Return (%)",
        xaxis=dict(showgrid=False, linecolor='#d2d2d7'),
        yaxis=dict(showgrid=True, gridcolor='#f5f5f7', linecolor='#d2d2d7', ticksuffix="%"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

def generate_bulletproof_matrix(daily_df: pd.DataFrame):
    df = daily_df.copy()
    df['Year'] = df['Date'].dt.year
    df['Month'] = df['Date'].dt.month
    
    monthly_pnl = df.groupby(['Year', 'Month'])['PNL'].sum()
    monthly_return = (monthly_pnl / INITIAL_INVESTMENT) * 100
    pivot_table = monthly_return.unstack()
    
    months_map = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun', 
                  7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}
    pivot_table = pivot_table.rename(columns=months_map)
    
    for m in months_map.values():
        if m not in pivot_table.columns:
            pivot_table[m] = np.nan
            
    pivot_table = pivot_table[list(months_map.values())]
    pivot_table['YTD'] = pivot_table.sum(axis=1)
    
    # Format natively as strings to completely avoid Pandas Styler attribute errors
    for col in pivot_table.columns:
        pivot_table[col] = pivot_table[col].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "-")
        
    return pivot_table.reset_index()

# --- 4. STRATEGY CONTENT DICTIONARY ---
STRATEGIES = {
    "Olho Diário": {
        "file": "olho_logbook.csv",
        "type": "Intraday Quantitative Equity Portfolio",
        "audience": "Qualified Investors",
        "fee": "2.00% p.a. | 20% > Benchmark",
        "desc": "The Olho Diário strategy is a sophisticated intraday quantitative equity portfolio engineered to isolate and capitalize on immediate market momentum, gap imbalances, and structural price reversals. At its core, this framework was developed to introduce high predictability into intraday trading by leveraging mathematical patterns established in preceding market sessions. Unlike traditional models that rely on static technical indicators, the Olho Diário engine dynamically develops a daily targeted portfolio consisting of the 20 highest-probability equities in the Brazilian market. To achieve this, the algorithm subjects each asset to a rigorous stress test, simulating over 2,000 unique scenarios daily. It continuously retrains its model using OHLC data and current-day opening auction values to identify forward-looking, highly profitable entry routes.\n\nA defining characteristic of this strategy is its strict adherence to intraday execution. By ensuring that all positions are opened and closed within the same trading session, the portfolio maintains zero overnight exposure. This structural mandate acts as a powerful shield against macroeconomic shocks and unpredictable overnight gap risks. Furthermore, capital allocation is highly distributed across the selected assets, preventing concentration risk and ensuring that no single market cycle can fracture the strategy's foundation."
    },
    "Quantitative Alpha - B3": {
        "file": "market_neutral_logbook.csv",
        "type": "Intraday Market-Neutral Statistical Arbitrage",
        "audience": "Professional Investors",
        "fee": "2.00% p.a. | 20% > Benchmark",
        "desc": "Quantitative Alpha - B3 is an institutional-grade, market-neutral statistical arbitrage strategy designed exclusively to exploit behavioral overreactions during the highly volatile market open. Moving away from traditional technical analysis or directional betting, this model relies entirely on Volatility-Adjusted Relative Extremes. The algorithm precisely isolates the overnight price action—the gap between the previous day's close and the current day's open—across the entire IBOV universe. It then divides this raw gap by each specific stock's 20-day historical standard deviation. This critical normalization process converts a simple percentage gap into a rigorous statistical Z-Score, allowing the engine to measure exactly how abnormal a morning gap is relative to that specific asset's historical behavioral baseline.\n\nAt exactly 9:30 AM, the algorithmic engine cross-sectionally ranks the analyzed universe based on these Z-Scores. It then constructs a perfectly balanced, market-neutral portfolio designed to act as a liquidity provider during early morning chaos. The system automatically executes long positions on the most severely suppressed gaps—fading morning retail panic—and simultaneously takes short positions on the most heavily inflated gaps, fading morning euphoria. By anchoring itself to both sides of the market evenly, the strategy entirely neutralizes broader market directional risk (Beta)."
    },
    "LAM Strategy": {
        "file": "lam_strategy_logbook.csv",
        "type": "Auto-Adaptive Multi-Model Swing Portfolio",
        "audience": "Qualified Investors",
        "fee": "2.00% p.a. | 20% > Benchmark",
        "desc": "The flagship LAM Strategy is a highly advanced, auto-adaptive swing trading portfolio driven by a robust ensemble of seven distinct quantitative models. Designed to navigate and conquer complex, multi-day market cycles, the foundation of this strategy rests heavily on rigorous statistical mathematics rather than conventional charting. The primary engine utilizes the Hurst Exponent to continuously monitor and detect shifting market regimes—accurately distinguishing between trending (persistent) and mean-reverting (anti-persistent) environments. Concurrently, it applies Ornstein-Uhlenbeck processes to calculate mathematically optimal mean-reversion half-lives, dictating exactly how long a swing position should be held.\n\nDepending on the detected regime, the algorithmic framework dynamically rotates capital across its sub-strategies. These include models targeting extreme Volatility Compression, Volume Climaxes, adaptive Keltner Squeezes, and Anchored VWAP Divergences. Unlike our strictly intraday models, the LAM Strategy is designed to hold overnight exposure, capturing larger multi-day alpha. Risk is managed asymmetrically via dynamic, volatility-adjusted Stop-Loss and Take-Profit brackets. Crucially, the engine features an institutional 'Mirror Book' parameter, allowing the algorithm to seamlessly invert its entire signal logic if macroeconomic headwinds dictate severe structural system decay."
    },
    "Swing Trade ATR": {
        "file": "swing_atr_logbook.csv",
        "type": "Systematic Scale-In Portfolio Matrix",
        "audience": "Qualified Investors",
        "fee": "1.50% p.a. | 20% > Benchmark",
        "desc": "The Swing Trade ATR framework is an institutional-grade, multi-tranche scale-in engine engineered to systematically build positions during extreme pricing anomalies. At its core, the strategy is predicated on the mathematical certainty of mean reversion, utilizing a 20-day Exponential Weighted Moving Average (EWMA) as the fundamental baseline for fair value. Rather than executing a single, rigid entry, the portfolio manager module deploys capital across five calculated tranches, scaling into positions as an asset deviates further from its baseline.\n\nTo ensure mathematical precision, these scale-in levels are strictly guarded by Average True Range (ATR) volatility bands. As an asset drops 2.0, 3.0, 4.5, 6.0, and ultimately 8.0 ATR multiples below its EWMA, the engine progressively increases its capital allocation weighting. However, to prevent the system from blindly catching 'falling knives', the strategy employs a rolling 60-day Hurst exponent as an absolute regime filter. If the Hurst calculation indicates a persistent downward trend, the scale-in logic is instantly aborted. The entire aggregate position is closed the moment the asset's price reverts to the rolling EWMA baseline, ensuring strictly defined downside risk parameters."
    }
}

# --- 5. SIDEBAR & FILE LOADING ---
with st.sidebar:
    st.markdown("## LAM CAPITAL")
    st.markdown("<p style='color:#86868b; font-size: 0.9rem; margin-top:-10px;'>Quantitative Asset Management</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    selected_strategy = st.radio("Select Strategy Factsheet:", options=list(STRATEGIES.keys()))
    strat_meta = STRATEGIES[selected_strategy]
    expected_filename = strat_meta["file"]
    
    st.markdown("---")
    uploaded_file = st.file_uploader(f"Upload {expected_filename} to sync data:", type=['csv'])

# --- 6. MAIN FACTSHEET BODY ---
raw_df = load_and_clean_data(expected_filename, uploaded_file)

if raw_df is None:
    st.warning(f"⚠️ **Waiting for Data:** Please upload **{expected_filename}** via the sidebar to generate the factsheet.")
    st.stop()

daily_df, total_ret, pct_bench, pos_months, neg_months, max_dd, max_m_ret, min_m_ret = calculate_kpis(raw_df)

# HEADER
st.markdown(f"<h1>{selected_strategy}</h1>", unsafe_allow_html=True)
st.markdown(f"<h3 style='margin-top:-5px;'>{strat_meta['type']}</h3>", unsafe_allow_html=True)

# SUMMARY TEXT (200-400 words)
paragraphs = strat_meta["desc"].split("\n\n")
for p in paragraphs:
    st.markdown(f"<p>{p}</p>", unsafe_allow_html=True)

# CHART
st.markdown("<h2>Cumulative Performance</h2>", unsafe_allow_html=True)
chart = build_prospectus_chart(daily_df, selected_strategy)
st.plotly_chart(chart, use_container_width=True)

# MATRIX
st.markdown("<h2>Monthly Return Matrix</h2>", unsafe_allow_html=True)
matrix = generate_bulletproof_matrix(daily_df)
st.dataframe(matrix, use_container_width=True, hide_index=True)

# PROSPECTUS DETAILS (2 Columns mimicking the PDF)
col1, col_space, col2 = st.columns([1, 0.1, 1])

with col1:
    st.markdown("<h2>Risk & Performance Analysis</h2>", unsafe_allow_html=True)
    st.markdown(f"""
    <table class="info-table">
        <tr><th>Return Since Inception</th><td>{total_ret:.2f}%</td></tr>
        <tr><th>Return Since Inception (% Benchmark)</th><td>{pct_bench:.2f}%</td></tr>
        <tr><th>Positive Months</th><td>{pos_months}</td></tr>
        <tr><th>Negative Months</th><td>{neg_months}</td></tr>
        <tr><th>Maximum Drawdown</th><td>{max_dd:.2f}%</td></tr>
        <tr><th>Max Monthly Return</th><td>{max_m_ret:.2f}%</td></tr>
        <tr><th>Min Monthly Return</th><td>{min_m_ret:.2f}%</td></tr>
    </table>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("<h2>General Information</h2>", unsafe_allow_html=True)
    start_date = daily_df['Date'].iloc[0].strftime('%B %d, %Y') if not daily_df.empty else "N/A"
    st.markdown(f"""
    <table class="info-table">
        <tr><th>Inception Date</th><td>{start_date}</td></tr>
        <tr><th>Target Audience</th><td>{strat_meta['audience']}</td></tr>
        <tr><th>Fees</th><td>{strat_meta['fee']}</td></tr>
        <tr><th>Redemption Liquidity</th><td>T+0 (Intraday) / T+2 (Swing)</td></tr>
        <tr><th>Initial Minimum Allocation</th><td>$ 1,000,000</td></tr>
        <tr><th>Custodian</th><td>BTG Pactual</td></tr>
        <tr><th>Auditor</th><td>KPMG</td></tr>
    </table>
    """, unsafe_allow_html=True)

st.markdown("---")
st.markdown("<p style='font-size:0.8rem; color:#86868b; text-align:center;'>This material is for informational purposes only and does not constitute investment advice. Past performance is not indicative of future results.</p>", unsafe_allow_html=True)
