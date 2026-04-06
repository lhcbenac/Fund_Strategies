import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import streamlit.components.v1 as components

# --- 1. PAGE CONFIGURATION & STYLING ---
st.set_page_config(
    page_title="LAM Capital | Factsheet",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Advanced Institutional CSS & Print Media Queries
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
        
        /* Native PDF Formatting (Triggered via Ctrl+P or the Print Button) */
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

# --- 2. GLOBAL CONSTANTS ---
INITIAL_INVESTMENT = 1000000.0  
ANNUAL_BENCHMARK_RATE = 0.15  # 15% Annual Benchmark
DAILY_BENCHMARK_RATE = ANNUAL_BENCHMARK_RATE / 252

# --- 3. CORE LOGIC & METRICS ---

@st.cache_data
def load_data(filename: str):
    """Load CSV and normalize the date column (supports Date, Loop_Date, etc.)."""
    if not os.path.exists(filename):
        return None
    try:
        df = pd.read_csv(filename)

        # Normalize column names
        df.columns = df.columns.str.strip()

        # Accept multiple possible date column names
        date_candidates = ['Date', 'Loop_Date', 'Trade_Date', 'date']
        date_col = next((c for c in date_candidates if c in df.columns), None)

        if date_col is None:
            return None

        # Rename chosen date column to 'Date' so the rest of the code works unchanged
        if date_col != 'Date':
            df = df.rename(columns={date_col: 'Date'})

        # Parse dates and clean
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])

        return df.sort_values('Date').reset_index(drop=True)
    except Exception:
        return None


def preprocess_strategy_df(df: pd.DataFrame, strategy_name: str) -> pd.DataFrame:
    """
    Strategy‑specific adjustments.

    For 'Olho Diário':
      - PNL column is in cents per share.
      - Use Gatilho as entry price.
      - Position per entry = 50k BRL.
      - Lot size rounded to nearest 100 shares.
      - Cash PNL = PNL_per_share * lot_size.
    For others:
      - Assume PNL already in cash.
    """
    df = df.copy()

    # Ensure we have a PNL column
    if 'PNL' not in df.columns:
        return df

    if strategy_name == "Olho Diário":
        # Use Gatilho as entry price
        price_col_candidates = ['Gatilho', 'Close_D0', 'Close']
        price_col = next((c for c in price_col_candidates if c in df.columns), None)

        if price_col is None:
            # Fallback: convert PNL from cents to cash but cannot size by price
            df['PNL'] = pd.to_numeric(df['PNL'], errors='coerce') / 100.0
            df = df.dropna(subset=['PNL'])
            return df

        # Force numeric types
        df['PNL'] = pd.to_numeric(df['PNL'], errors='coerce')
        df[price_col] = pd.to_numeric(df[price_col], errors='coerce')

        # Drop rows where price or PNL is invalid or non-positive
        df = df.dropna(subset=['PNL', price_col])
        df = df[df[price_col] > 0]

        if df.empty:
            return df

        # Convert PNL from cents to cash (per share)
        df['PNL_per_share'] = df['PNL'] / 100.0

        # Position per entry is fixed 50k BRL
        POSITION_VALUE = 50000.0

        # Compute raw share quantity = position value / price
        df['raw_qty'] = POSITION_VALUE / df[price_col]

        # Round quantity to nearest multiple of 100 (Brazil lot)
        df['lot_size'] = (df['raw_qty'] / 100).round().astype(int) * 100

        # Ensure lot_size is at least 100 (avoid 0 lots)
        df.loc[df['lot_size'] <= 0, 'lot_size'] = 100

        # Cash PNL = PNL_per_share * lot_size
        df['PNL_cash'] = df['PNL_per_share'] * df['lot_size']

        # Use cash PNL as the main PNL the rest of the app sees
        df['PNL'] = df['PNL_cash']

        # Clean helper columns if you want
        df = df.drop(columns=['PNL_per_share', 'raw_qty'], errors='ignore')

    else:
        # Other strategies: ensure PNL is numeric and treat as cash
        df['PNL'] = pd.to_numeric(df['PNL'], errors='coerce')
        df = df.dropna(subset=['PNL'])

    return df


def calculate_kpis(df: pd.DataFrame):
    daily = df.groupby(df['Date'].dt.date)['PNL'].sum().reset_index()
    daily['Date'] = pd.to_datetime(daily['Date'])
    
    daily['Cumulative_PNL'] = daily['PNL'].cumsum()
    daily['NAV'] = INITIAL_INVESTMENT + daily['Cumulative_PNL']
    
    daily['Strat_Cum_Ret'] = (daily['Cumulative_PNL'] / INITIAL_INVESTMENT) * 100
    daily['Bench_Cum_Ret'] = ((1 + DAILY_BENCHMARK_RATE) ** np.arange(1, len(daily) + 1) - 1) * 100
    
    daily['YearMonth'] = daily['Date'].dt.to_period('M')
    monthly_returns = daily.groupby('YearMonth')['PNL'].sum()
    pos_months = (monthly_returns > 0).sum()
    neg_months = (monthly_returns < 0).sum()
    
    total_ret = daily['Strat_Cum_Ret'].iloc[-1] if not daily.empty else 0
    bench_ret = daily['Bench_Cum_Ret'].iloc[-1] if not daily.empty else 0
    pct_bench = (total_ret / bench_ret) * 100 if bench_ret != 0 else 0
    
    rolling_max = daily['NAV'].cummax()
    drawdown = ((daily['NAV'] - rolling_max) / rolling_max) * 100
    max_dd = drawdown.min()
    
    max_m_ret = (monthly_returns.max() / INITIAL_INVESTMENT) * 100 if not monthly_returns.empty else 0
    min_m_ret = (monthly_returns.min() / INITIAL_INVESTMENT) * 100 if not monthly_returns.empty else 0

    return daily, total_ret, pct_bench, pos_months, neg_months, max_dd, max_m_ret, min_m_ret


def build_prospectus_chart(daily_df: pd.DataFrame, strategy_name: str):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily_df['Date'], y=daily_df['Bench_Cum_Ret'],
        mode='lines', name='Benchmark (10% a.a.)',
        line=dict(color='#86868b', width=2, dash='dot')
    ))
    fig.add_trace(go.Scatter(
        x=daily_df['Date'], y=daily_df['Strat_Cum_Ret'],
        mode='lines', name=strategy_name,
        line=dict(color='#0071e3', width=2.5), 
        fill='tonexty', fillcolor='rgba(0, 113, 227, 0.08)',
        hovertemplate="<b>%{x|%b %d, %Y}</b><br>Return: %{y:.2f}%<extra></extra>"
    ))
    fig.update_layout(
        plot_bgcolor='#ffffff', paper_bgcolor='#ffffff',
        margin=dict(l=0, r=0, t=10, b=0),
        height=420, hovermode='x unified',
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
    
    for col in pivot_table.columns:
        pivot_table[col] = pivot_table[col].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "-")
        
    return pivot_table.reset_index()


# --- 4. STRATEGY DICTIONARY ---
STRATEGIES = {
    "Olho Diário": {
        "file": "olho_logbook.csv",
        "type": "Intraday Quantitative Equity Portfolio",
        "audience": "Qualified Investors",
        "fee": "2.00% p.a. | 20% > Benchmark",
        "desc": "The Olho Diário strategy is a sophisticated intraday quantitative equity portfolio engineered to isolate and capitalize on immediate market momentum, gap imbalances, and structural price reversals. At its core, this framework was developed to introduce high predictability into intraday trading by leveraging mathematical patterns established in preceding market sessions. Unlike traditional models that rely on static technical indicators, the Olho Diário engine dynamically develops a daily targeted portfolio consisting of the 20 highest-probability equities in the Brazilian market. To achieve this, the algorithm subjects each asset to a rigorous stress test, simulating over 2,000 unique scenarios daily. It continuously retrains its model using OHLC data and current-day opening auction values to identify forward-looking, highly profitable entry routes.\\n\\nA defining characteristic of this strategy is its strict adherence to intraday execution. By ensuring that all positions are opened and closed within the same trading session, the portfolio maintains zero overnight exposure. This structural mandate acts as a powerful shield against macroeconomic shocks and unpredictable overnight gap risks. Furthermore, capital allocation is highly distributed across the selected assets, preventing concentration risk and ensuring that no single market cycle can fracture the strategy's foundation."
    },
    "Quantitative Alpha - B3": {
        "file": "market_neutral_logbook.csv",
        "type": "Intraday Market-Neutral Statistical Arbitrage",
        "audience": "Professional Investors",
        "fee": "2.00% p.a. | 20% > Benchmark",
        "desc": "Quantitative Alpha - B3 is an institutional-grade, market-neutral statistical arbitrage framework engineered to exploit behavioral mispricings following the market open. To eliminate the execution paradox of trading during the unpredictable pre-market auction, this strategy employs a Delayed Execution Limit Engine.\\n\\nAt exactly 10:00 AM, the algorithm calculates the overnight price gap across the entire IBOV universe using the actual opening prices. It normalizes these gaps against a rolling 20-day historical volatility baseline to generate Volatility-Adjusted Z-Scores. The system then cross-sectionally ranks the universe, identifying the Top 5 most suppressed gaps (Morning Panic / Long Targets) and the Top 5 most inflated gaps (Morning Euphoria / Short Targets).\\n\\nRather than executing aggressive Market-On-Open orders, the system deploys opportunistic limit orders. For Long targets, it posts bids exactly 1.00% below the opening price. For Short targets, it posts offers exactly 1.00% above the opening price. The algorithm then waits. A trade is only executed if intraday volatility spikes enough to fill these favorable limit prices. If an asset simply drifts away without triggering the pullback, the system gracefully aborts the trade, preserving capital. Once a limit order is filled, the strategy captures intraday mean-reversion as the asset gravitates toward fair value, closing all positions rigidly by the end of the session."
    },
    "LAM Strategy": {
        "file": "lam_strategy_logbook.csv",
        "type": "Auto-Adaptive Multi-Model Swing Portfolio",
        "audience": "Qualified Investors",
        "fee": "2.00% p.a. | 20% > Benchmark",
        "desc": "The flagship LAM Strategy is a highly advanced, auto-adaptive swing trading portfolio driven by a robust ensemble of seven distinct quantitative models. Designed to navigate and conquer complex, multi-day market cycles, the foundation of this strategy rests heavily on rigorous statistical mathematics rather than conventional charting. The primary engine utilizes the Hurst Exponent to continuously monitor and detect shifting market regimes—accurately distinguishing between trending (persistent) and mean-reverting (anti-persistent) environments. Concurrently, it applies Ornstein-Uhlenbeck processes to calculate mathematically optimal mean-reversion half-lives, dictating exactly how long a swing position should be held.\\n\\nDepending on the detected regime, the algorithmic framework dynamically rotates capital across its sub-strategies. These include models targeting extreme Volatility Compression, Volume Climaxes, adaptive Keltner Squeezes, and Anchored VWAP Divergences. Unlike our strictly intraday models, the LAM Strategy is designed to hold overnight exposure, capturing larger multi-day alpha. Risk is managed asymmetrically via dynamic, volatility-adjusted Stop-Loss and Take-Profit brackets. Crucially, the engine features an institutional 'Mirror Book' parameter, allowing the algorithm to seamlessly invert its entire signal logic if macroeconomic headwinds dictate severe structural system decay."
    },
    "Swing Trade ATR": {
        "file": "swing_atr_logbook.csv",
        "type": "Systematic Scale-In Portfolio Matrix",
        "audience": "Qualified Investors",
        "fee": "1.50% p.a. | 20% > Benchmark",
        "desc": "The Swing Trade ATR framework is an institutional-grade, multi-tranche scale-in engine engineered to systematically build positions during extreme pricing anomalies. At its core, the strategy is predicated on the mathematical certainty of mean reversion, utilizing a 20-day Exponential Weighted Moving Average (EWMA) as the fundamental baseline for fair value. Rather than executing a single, rigid entry, the portfolio manager module deploys capital across five calculated tranches, scaling into positions as an asset deviates further from its baseline.\\n\\nTo ensure mathematical precision, these scale-in levels are strictly guarded by Average True Range (ATR) volatility bands. As an asset drops 2.0, 3.0, 4.5, 6.0, and ultimately 8.0 ATR multiples below its EWMA, the engine progressively increases its capital allocation weighting. However, to prevent the system from blindly catching 'falling knives', the strategy employs a rolling 60-day Hurst exponent as an absolute regime filter. If the Hurst calculation indicates a persistent downward trend, the scale-in logic is instantly aborted. The entire aggregate position is closed the moment the asset's price reverts to the rolling EWMA baseline, ensuring strictly defined downside risk parameters."
    }
}

# --- 5. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.markdown("## LAM CAPITAL")
    st.markdown("<p style='color:#86868b; font-size: 0.9rem; margin-top:-10px;'>Quantitative Asset Management</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    selected_strategy = st.radio("Select Portfolio Factsheet:", options=list(STRATEGIES.keys()))
    strat_meta = STRATEGIES[selected_strategy]
    expected_filename = strat_meta["file"]
    
    st.markdown("---")
    st.markdown("<small style='color:#86868b;'>CONFIDENTIAL PROSPECTUS</small>", unsafe_allow_html=True)

# --- 6. DATA SYNCHRONIZATION CHECK ---
raw_df = load_data(expected_filename)

if raw_df is None or raw_df.empty:
    st.info(
        f"**System Notice:** The execution ledger for `{selected_strategy}` is currently synchronizing or unavailable. "
        f"Please ensure `{expected_filename}` is present in the deployment repository and contains a valid date column.",
        icon="ℹ️"
    )
    st.stop()

# Apply strategy‑specific transformations
proc_df = preprocess_strategy_df(raw_df, selected_strategy)

if proc_df is None or proc_df.empty:
    st.info(
        f"**System Notice:** After processing, there are no valid records for `{selected_strategy}` "
        f"(check `PNL` and `Gatilho` columns).",
        icon="ℹ️"
    )
    st.stop()

daily_df, total_ret, pct_bench, pos_months, neg_months, max_dd, max_m_ret, min_m_ret = calculate_kpis(proc_df)

# --- 7. MAIN FACTSHEET BODY ---
col_title, col_actions = st.columns([2.5, 1])

with col_title:
    st.markdown(f"<h1>{selected_strategy}</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='margin-top:-5px;'>{strat_meta['type']}</h3>", unsafe_allow_html=True)

with col_actions:
    st.write("") 
    # Action 1: Export CSV (processed ledger so PNL is cash-consistent)
    csv_bytes = proc_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="⬇️ Export Ledger (.csv)",
        data=csv_bytes,
        file_name=expected_filename,
        mime="text/csv",
        use_container_width=True
    )
    # Action 2: Trigger Native Print-to-PDF Dialog
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
        height=50
    )

st.markdown("---")

# Strategy Narrative
paragraphs = strat_meta["desc"].split("\\n\\n")
for p in paragraphs:
    st.markdown(f"<p>{p}</p>", unsafe_allow_html=True)

# Performance Chart
st.markdown("<h2>Cumulative Performance Evolution</h2>", unsafe_allow_html=True)
chart = build_prospectus_chart(daily_df, selected_strategy)
st.plotly_chart(chart, use_container_width=True, config={'displayModeBar': False})

# Return Matrix
st.markdown("<h2>Monthly Return Matrix</h2>", unsafe_allow_html=True)
matrix = generate_bulletproof_matrix(daily_df)
st.dataframe(matrix, use_container_width=True, hide_index=True)

# Institutional Details
col1, col_space, col2 = st.columns([1, 0.1, 1])

with col1:
    st.markdown("<h2>Risk & Performance Metrics</h2>", unsafe_allow_html=True)
    st.markdown(f"""
    <table class="info-table">
        <tr><th>Return Since Inception</th><td>{total_ret:.2f}%</td></tr>
        <tr><th>Return (% Benchmark)</th><td>{pct_bench:.2f}%</td></tr>
        <tr><th>Positive Months</th><td>{pos_months}</td></tr>
        <tr><th>Negative Months</th><td>{neg_months}</td></tr>
        <tr><th>Maximum Drawdown</th><td>{max_dd:.2f}%</td></tr>
        <tr><th>Best Monthly Return</th><td>{max_m_ret:.2f}%</td></tr>
        <tr><th>Worst Monthly Return</th><td>{min_m_ret:.2f}%</td></tr>
    </table>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("<h2>General Information</h2>", unsafe_allow_html=True)
    start_date = daily_df['Date'].iloc[0].strftime('%B %d, %Y') if not daily_df.empty else "N/A"
    st.markdown(f"""
    <table class="info-table">
        <tr><th>Inception Date</th><td>{start_date}</td></tr>
        <tr><th>Target Audience</th><td>{strat_meta['audience']}</td></tr>
        <tr><th>Management & Perf. Fee</th><td>{strat_meta['fee']}</td></tr>
        <tr><th>Redemption Liquidity</th><td>T+30</td></tr>
        <tr><th>Minimum Allocation</th><td>$ 1,000,000</td></tr>
        <tr><th>Capital Mandate</th><td>Absolute Return</td></tr>
    </table>
    """, unsafe_allow_html=True)

st.markdown("---")
st.markdown("<p style='font-size:0.8rem; color:#86868b; text-align:center;'>This material is strictly for informational purposes and does not constitute an offer to sell or a solicitation to buy any securities. Past performance is not indicative of future results.</p>", unsafe_allow_html=True)
