import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import calendar
import os

# --- 1. PAGE CONFIGURATION & CSS INJECTION ---
st.set_page_config(
    page_title="LAM Capital | Quantitative Strategies",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sophisticated, institutional CSS
st.markdown("""
    <style>
        /* Base typography */
        html, body, [class*="css"] {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            color: #1d1d1f;
        }
        
        /* Metric Cards */
        .metric-card {
            background-color: #f5f5f7;
            border: 1px solid #d2d2d7;
            border-radius: 8px;
            padding: 20px;
            text-align: left;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }
        .metric-title {
            font-size: 0.85rem;
            color: #86868b;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
            font-weight: 600;
        }
        .metric-value {
            font-size: 1.8rem;
            color: #1d1d1f;
            font-weight: 700;
        }
        
        /* Tab Styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 24px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: transparent;
            border-radius: 4px 4px 0px 0px;
            padding-top: 10px;
            padding-bottom: 10px;
            font-size: 1.05rem;
            font-weight: 500;
        }
        .stTabs [aria-selected="true"] {
            border-bottom: 3px solid #0071e3 !important;
            color: #0071e3 !important;
        }
        
        /* Clean UI */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 2. GLOBAL CONSTANTS ---
INITIAL_INVESTMENT = 1000000.0  
RISK_FREE_RATE = 0.10 / 252 # Assumed 10% annual benchmark 

# --- 3. CORE LOGIC & DATA PROCESSING ---

@st.cache_data
def load_and_clean_data(filename: str, uploaded_file=None):
    """Robust data loader prioritizing uploaded files over local paths."""
    try:
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
        elif os.path.exists(filename):
            df = pd.read_csv(filename)
        else:
            return None
            
        df['Date'] = pd.to_datetime(df['Date'])
        # Sort chronologically
        df = df.sort_values('Date').reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"Error reading data: {e}")
        return None

def calculate_kpis(df: pd.DataFrame):
    """Calculates institutional-grade metrics."""
    # Aggregate to daily in case of multiple intraday entries
    daily = df.groupby(df['Date'].dt.date)['PNL'].sum().reset_index()
    daily['Date'] = pd.to_datetime(daily['Date'])
    
    daily['Cumulative_PNL'] = daily['PNL'].cumsum()
    daily['NAV'] = INITIAL_INVESTMENT + daily['Cumulative_PNL']
    
    # Avoid division by zero on the first day
    shifted_nav = daily['NAV'].shift(1).fillna(INITIAL_INVESTMENT)
    daily['Daily_Return'] = daily['PNL'] / shifted_nav
    
    days_trading = len(daily)
    if days_trading == 0:
        return daily, 0, 0, 0, 0, 0
        
    overall_return_pct = (daily['Cumulative_PNL'].iloc[-1] / INITIAL_INVESTMENT) * 100
    
    # Advanced Metrics
    mean_return = daily['Daily_Return'].mean()
    std_return = daily['Daily_Return'].std()
    
    ann_volatility = std_return * np.sqrt(252) * 100
    sharpe_ratio = ((mean_return - RISK_FREE_RATE) / std_return) * np.sqrt(252) if std_return != 0 else 0
    
    rolling_max = daily['NAV'].cummax()
    drawdown = (daily['NAV'] - rolling_max) / rolling_max
    max_drawdown = drawdown.min() * 100
    
    win_rate = (len(daily[daily['PNL'] > 0]) / days_trading) * 100
    
    return daily, days_trading, overall_return_pct, sharpe_ratio, max_drawdown, ann_volatility, win_rate

def render_metric_card(title, value):
    """Generates custom HTML for a sleek metric card."""
    return f"""
    <div class="metric-card">
        <div class="metric-title">{title}</div>
        <div class="metric-value">{value}</div>
    </div>
    """

def build_advanced_chart(daily_df: pd.DataFrame, strategy_name: str):
    """Builds an objective, high-density Plotly chart."""
    fig = go.Figure()
    
    # Base Capital Line
    fig.add_trace(go.Scatter(
        x=[daily_df['Date'].iloc[0], daily_df['Date'].iloc[-1]], 
        y=[INITIAL_INVESTMENT, INITIAL_INVESTMENT],
        mode='lines', name='Initial Capital ($1M)',
        line=dict(color='#86868b', width=1, dash='dash'),
        hoverinfo='skip'
    ))

    # NAV Curve
    fig.add_trace(go.Scatter(
        x=daily_df['Date'], y=daily_df['NAV'],
        mode='lines', name=strategy_name,
        line=dict(color='#0071e3', width=2), 
        fill='tozeroy', fillcolor='rgba(0, 113, 227, 0.08)',
        hovertemplate="<b>Date:</b> %{x|%Y-%m-%d}<br><b>NAV:</b> $%{y:,.2f}<extra></extra>"
    ))

    fig.update_layout(
        plot_bgcolor='#ffffff', paper_bgcolor='#ffffff',
        margin=dict(l=0, r=0, t=10, b=0),
        height=450, hovermode='x unified',
        xaxis=dict(
            showgrid=False, linecolor='#d2d2d7', 
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1M", step="month", stepmode="backward"),
                    dict(count=3, label="3M", step="month", stepmode="backward"),
                    dict(count=6, label="6M", step="month", stepmode="backward"),
                    dict(step="all", label="ALL")
                ])
            )
        ),
        yaxis=dict(showgrid=True, gridcolor='#f5f5f7', linecolor='#d2d2d7', tickprefix="$"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

def generate_styled_monthly_matrix(daily_df: pd.DataFrame):
    """Creates a heat-mapped cross-tabulation of returns."""
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
    
    # Pandas Styler for Conditional Formatting
    def color_returns(val):
        if pd.isna(val): return ''
        color = '#e7f3eb' if val > 0 else '#fbebea' if val < 0 else ''
        text_color = '#1e4620' if val > 0 else '#8a2522' if val < 0 else ''
        return f'background-color: {color}; color: {text_color}'
        
    styled_table = pivot_table.style.applymap(color_returns)\
                                    .format("{:.2f}%", na_rep="-")
    return styled_table

# --- 4. STRATEGY CONTENT DICTIONARY ---
STRATEGIES = {
    "Olho Diário": {
        "file": "olho_logbook.csv",
        "type": "Intraday Quantitative Equity Portfolio",
        "desc": "The Olho Diário strategy is a sophisticated intraday quantitative equity portfolio engineered to isolate and capitalize on immediate market momentum, gap imbalances, and structural price reversals. At its core, this framework was developed to introduce high predictability into intraday trading by leveraging mathematical patterns established in preceding market sessions. Unlike traditional models that rely on static technical indicators, the Olho Diário engine dynamically develops a daily targeted portfolio consisting of the 20 highest-probability equities in the Brazilian market. To achieve this, the algorithm subjects each asset to a rigorous stress test, simulating over 2,000 unique scenarios daily. It continuously retrains its model using OHLC data and current-day opening auction values to identify forward-looking, highly profitable entry routes.\n\nA defining characteristic of this strategy is its strict adherence to intraday execution. By ensuring that all positions are opened and closed within the same trading session, the portfolio maintains zero overnight exposure. This structural mandate acts as a powerful shield against macroeconomic shocks and unpredictable overnight gap risks. Furthermore, capital allocation is highly distributed across the selected assets, preventing concentration risk and ensuring that no single market cycle can fracture the strategy's foundation."
    },
    "Quantitative Alpha - B3": {
        "file": "market_neutral_logbook.csv",
        "type": "Intraday Market-Neutral Statistical Arbitrage",
        "desc": "Quantitative Alpha - B3 is an institutional-grade, market-neutral statistical arbitrage strategy designed exclusively to exploit behavioral overreactions during the highly volatile market open. Moving away from traditional technical analysis or directional betting, this model relies entirely on Volatility-Adjusted Relative Extremes. The algorithm precisely isolates the overnight price action—the gap between the previous day's close and the current day's open—across the entire IBOV universe. It then divides this raw gap by each specific stock's 20-day historical standard deviation. This critical normalization process converts a simple percentage gap into a rigorous statistical Z-Score, allowing the engine to measure exactly how abnormal a morning gap is relative to that specific asset's historical behavioral baseline.\n\nAt exactly 9:30 AM, the algorithmic engine cross-sectionally ranks the analyzed universe based on these Z-Scores. It then constructs a perfectly balanced, market-neutral portfolio designed to act as a liquidity provider during early morning chaos. The system automatically executes long positions on the most severely suppressed gaps—fading morning retail panic—and simultaneously takes short positions on the most heavily inflated gaps, fading morning euphoria. By anchoring itself to both sides of the market evenly, the strategy entirely neutralizes broader market directional risk (Beta)."
    },
    "LAM Strategy": {
        "file": "lam_strategy_logbook.csv",
        "type": "Auto-Adaptive Multi-Model Swing Portfolio",
        "desc": "The flagship LAM Strategy is a highly advanced, auto-adaptive swing trading portfolio driven by a robust ensemble of seven distinct quantitative models. Designed to navigate and conquer complex, multi-day market cycles, the foundation of this strategy rests heavily on rigorous statistical mathematics rather than conventional charting. The primary engine utilizes the Hurst Exponent to continuously monitor and detect shifting market regimes—accurately distinguishing between trending (persistent) and mean-reverting (anti-persistent) environments. Concurrently, it applies Ornstein-Uhlenbeck processes to calculate mathematically optimal mean-reversion half-lives, dictating exactly how long a swing position should be held.\n\nDepending on the detected regime, the algorithmic framework dynamically rotates capital across its sub-strategies. These include models targeting extreme Volatility Compression, Volume Climaxes, adaptive Keltner Squeezes, and Anchored VWAP Divergences. Unlike our strictly intraday models, the LAM Strategy is designed to hold overnight exposure, capturing larger multi-day alpha. Risk is managed asymmetrically via dynamic, volatility-adjusted Stop-Loss and Take-Profit brackets. Crucially, the engine features an institutional \"Mirror Book\" parameter, allowing the algorithm to seamlessly invert its entire signal logic if macroeconomic headwinds dictate severe structural system decay."
    },
    "Swing Trade ATR": {
        "file": "swing_atr_logbook.csv",
        "type": "Systematic Scale-In Portfolio Matrix",
        "desc": "The Swing Trade ATR framework is an institutional-grade, multi-tranche scale-in engine engineered to systematically build positions during extreme pricing anomalies. At its core, the strategy is predicated on the mathematical certainty of mean reversion, utilizing a 20-day Exponential Weighted Moving Average (EWMA) as the fundamental baseline for fair value. Rather than executing a single, rigid entry, the portfolio manager module deploys capital across five calculated tranches, scaling into positions as an asset deviates further from its baseline.\n\nTo ensure mathematical precision, these scale-in levels are strictly guarded by Average True Range (ATR) volatility bands. As an asset drops 2.0, 3.0, 4.5, 6.0, and ultimately 8.0 ATR multiples below its EWMA, the engine progressively increases its capital allocation weighting. However, to prevent the system from blindly catching 'falling knives', the strategy employs a rolling 60-day Hurst exponent as an absolute regime filter. If the Hurst calculation indicates a persistent downward trend, the scale-in logic is instantly aborted. The entire aggregate position is closed the moment the asset's price reverts to the rolling EWMA baseline, ensuring strictly defined downside risk parameters."
    }
}

# --- 5. APP LAYOUT & SIDEBAR ---
with st.sidebar:
    st.markdown("### LAM CAPITAL")
    st.markdown("<p style='color:#86868b; font-size: 0.9rem;'>Quantitative Asset Management</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    selected_strategy = st.radio("Select Active Framework:", options=list(STRATEGIES.keys()))
    strat_meta = STRATEGIES[selected_strategy]
    expected_filename = strat_meta["file"]
    
    st.markdown("---")
    st.markdown("### Data Synchronization")
    st.markdown(f"<p style='font-size:0.85rem; color:#515154;'>The system is looking for <b>{expected_filename}</b>.</p>", unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Upload manually if local file is missing:", 
        type=['csv'], 
        help="Upload the raw execution logbook to sync the dashboard."
    )
    
    st.markdown("<br><br><small style='color:#86868b'>CONFIDENTIAL PROSPECTUS</small>", unsafe_allow_html=True)

# --- 6. MAIN CONTENT BODY ---
st.title(selected_strategy)
st.markdown(f"**Classification:** {strat_meta['type']}")

# Load the Data safely
raw_df = load_and_clean_data(expected_filename, uploaded_file)

if raw_df is None:
    st.warning(f"⚠️ Unable to locate **{expected_filename}** in the root directory. Please upload the CSV using the sidebar to render the dashboard.")
    st.stop()

# If data loads successfully, calculate KPIs
daily_df, days, total_ret, sharpe, max_dd, ann_vol, win_rate = calculate_kpis(raw_df)

# Create 3 Clean Tabs
tab1, tab2, tab3 = st.tabs(["Performance Dashboard", "Strategy Architecture", "Execution Ledger"])

with tab1:
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Custom CSS Metric Cards (Row 1)
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: st.markdown(render_metric_card("Cum. Return", f"{total_ret:,.2f}%"), unsafe_allow_html=True)
    with col2: st.markdown(render_metric_card("Sharpe Ratio", f"{sharpe:.2f}"), unsafe_allow_html=True)
    with col3: st.markdown(render_metric_card("Max Drawdown", f"{max_dd:.2f}%"), unsafe_allow_html=True)
    with col4: st.markdown(render_metric_card("Ann. Volatility", f"{ann_vol:.2f}%"), unsafe_allow_html=True)
    with col5: st.markdown(render_metric_card("Win Rate", f"{win_rate:.1f}%"), unsafe_allow_html=True)
    
    st.markdown("<br><br><b>Net Asset Value (NAV) Evolution</b>", unsafe_allow_html=True)
    chart = build_advanced_chart(daily_df, selected_strategy)
    st.plotly_chart(chart, use_container_width=True)
    
    st.markdown("<br><b>Monthly Return Matrix</b>", unsafe_allow_html=True)
    monthly_matrix = generate_styled_monthly_matrix(daily_df)
    st.dataframe(monthly_matrix, use_container_width=True, height=250)

with tab2:
    st.markdown("<br>", unsafe_allow_html=True)
    # Split the long description into paragraphs for readability
    paragraphs = strat_meta["desc"].split("\n\n")
    for p in paragraphs:
        st.markdown(f"<p style='font-size: 1.05rem; color: #333333; line-height: 1.8;'>{p}</p>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.download_button(
        label="📄 Download Institutional Prospectus (PDF)",
        data=b"PDF_BYTE_DATA_PLACEHOLDER", # Replace with real generator if needed
        file_name=f"LAM_Capital_{selected_strategy.replace(' ', '_')}.pdf",
        mime="application/pdf"
    )

with tab3:
    st.markdown("<br><b>Raw Quantitative Execution Log</b>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:0.9rem; color:#86868b;'>Complete chronological ledger of all systemic entries, exits, and signals.</p>", unsafe_allow_html=True)
    
    st.dataframe(raw_df, use_container_width=True)
    
    csv_bytes = raw_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="⬇️ Export Complete Ledger (.csv)",
        data=csv_bytes,
        file_name=f"{strat_meta['file']}",
        mime="text/csv"
    )
