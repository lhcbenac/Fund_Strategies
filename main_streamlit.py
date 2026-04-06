import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import calendar
import os

# --- 1. PAGE CONFIGURATION & STYLING ---
st.set_page_config(
    page_title="LAM Capital | Strategy Prospectus",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        * { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        h1, h2, h3 { color: #1d1d1f; font-weight: 600; letter-spacing: -0.02em; }
        h1 { font-size: 2.5rem; margin-bottom: 0.5rem; }
        h2 { font-size: 1.5rem; margin-top: 2rem; border-bottom: 1px solid #d2d2d7; padding-bottom: 0.5rem;}
        p { color: #515154; font-size: 1.05rem; line-height: 1.6; }
        div[data-testid="stMetricValue"] { font-size: 1.8rem; font-weight: 600; color: #1d1d1f; }
        div[data-testid="stMetricLabel"] { font-size: 0.9rem; color: #86868b; text-transform: uppercase; letter-spacing: 0.05em;}
        .dataframe { font-size: 0.9rem; border-collapse: collapse; width: 100%; }
        .dataframe th { background-color: #f5f5f7; color: #1d1d1f; font-weight: 500; text-align: center; padding: 10px; border: 1px solid #d2d2d7;}
        .dataframe td { text-align: center; padding: 10px; border: 1px solid #d2d2d7; color: #515154; }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 2. GLOBAL CONSTANTS ---
INITIAL_INVESTMENT = 1000000.0  
RISK_FREE_RATE = 0.10 / 252 # Assumed 10% annual benchmark equivalent 

# --- 3. DATA PROCESSING FUNCTIONS ---
@st.cache_data
def load_strategy_data(filename: str) -> pd.DataFrame:
    if os.path.exists(filename):
        df = pd.read_csv(filename)
        df['Date'] = pd.to_datetime(df['Date'])
        return df.sort_values('Date')
    else:
        # Generate dummy data if CSV is not yet uploaded
        dates = pd.date_range(start='2024-03-12', end=pd.Timestamp.today(), freq='B')
        np.random.seed(len(filename)) 
        returns = np.random.normal(loc=0.0008, scale=0.006, size=len(dates))
        pnl = INITIAL_INVESTMENT * returns
        return pd.DataFrame({'Date': dates, 'PNL': pnl})

def calculate_metrics(df: pd.DataFrame):
    df = df.copy()
    daily_pnl = df.groupby(df['Date'].dt.date)['PNL'].sum().reset_index()
    daily_pnl['Date'] = pd.to_datetime(daily_pnl['Date'])
    
    daily_pnl['Cumulative_PNL'] = daily_pnl['PNL'].cumsum()
    daily_pnl['Capital'] = INITIAL_INVESTMENT + daily_pnl['Cumulative_PNL']
    daily_pnl['Daily_Return'] = daily_pnl['PNL'] / (daily_pnl['Capital'].shift(1).fillna(INITIAL_INVESTMENT))
    
    days_trading = len(daily_pnl)
    overall_return_abs = daily_pnl['Cumulative_PNL'].iloc[-1]
    overall_return_pct = (overall_return_abs / INITIAL_INVESTMENT) * 100
    
    mean_return = daily_pnl['Daily_Return'].mean()
    std_return = daily_pnl['Daily_Return'].std()
    sharpe_ratio = ((mean_return - RISK_FREE_RATE) / std_return) * np.sqrt(252) if std_return != 0 else 0
    
    rolling_max = daily_pnl['Capital'].cummax()
    drawdown = (daily_pnl['Capital'] - rolling_max) / rolling_max
    max_drawdown = drawdown.min() * 100
    
    return daily_pnl, days_trading, overall_return_pct, sharpe_ratio, max_drawdown

def plot_performance(daily_pnl: pd.DataFrame, strategy_name: str):
    fig = go.Figure()
    
    # Simulate a benchmark line
    benchmark_growth = INITIAL_INVESTMENT * (1 + (0.10/252)) ** np.arange(len(daily_pnl))
    
    fig.add_trace(go.Scatter(
        x=daily_pnl['Date'], y=benchmark_growth,
        mode='lines', name='Benchmark (10% Annualized)',
        line=dict(color='#1c3c54', width=2, dash='solid')
    ))

    fig.add_trace(go.Scatter(
        x=daily_pnl['Date'], y=daily_pnl['Capital'],
        mode='lines', name=strategy_name,
        line=dict(color='#0088cc', width=2), 
        fill='tonexty', fillcolor='rgba(0, 136, 204, 0.1)'
    ))

    fig.update_layout(
        plot_bgcolor='white', paper_bgcolor='white',
        margin=dict(l=0, r=0, t=20, b=0),
        height=450, hovermode='x unified',
        xaxis=dict(showgrid=False, linecolor='#d2d2d7', tickfont=dict(color='#86868b')),
        yaxis=dict(showgrid=True, gridcolor='#f5f5f7', linecolor='#d2d2d7', tickfont=dict(color='#86868b'), tickprefix="$"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

def generate_monthly_table(daily_pnl: pd.DataFrame):
    df = daily_pnl.copy()
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
    
    styled_table = pivot_table.applymap(lambda x: f"{x:.2f}%" if pd.notnull(x) else "-")
    return styled_table

# --- 4. STRATEGY CONTENT DICTIONARY ---
STRATEGIES = {
    "Olho Diário": {
        "file": "olho_logbook.csv",
        "type": "Intraday Quantitative Equity Portfolio",
        "description": """
        The Olho Diário strategy is a sophisticated intraday quantitative equity portfolio engineered to isolate and capitalize on immediate market momentum, gap imbalances, and structural price reversals. At its core, this framework was developed to introduce high predictability into intraday trading by leveraging mathematical patterns established in preceding market sessions. Unlike traditional models that rely on static technical indicators, the Olho Diário engine dynamically develops a daily targeted portfolio consisting of the 20 highest-probability equities in the Brazilian market. To achieve this, the algorithm subjects each asset to a rigorous stress test, simulating over 2,000 unique scenarios daily. It continuously retrains its model using OHLC (Open, High, Low, Close) data and current-day opening auction values to identify forward-looking, highly profitable entry routes.

        A defining characteristic of this strategy is its strict adherence to intraday execution. By ensuring that all positions are opened and closed within the same trading session, the portfolio maintains zero overnight exposure. This structural mandate acts as a powerful shield against macroeconomic shocks and unpredictable overnight gap risks. Furthermore, capital allocation is highly distributed across the selected assets, preventing concentration risk and ensuring that no single market cycle can fracture the strategy's foundation. Because the system is retrained daily, it possesses an exceptional capacity to pivot and adapt to shifting market regimes. This flexibility makes Olho Diário a versatile, adaptive solution for investors, providing consistent alpha generation and resilience in the face of high market volatility.
        """
    },
    "Quantitative Alpha - B3": {
        "file": "market_neutral_logbook.csv",
        "type": "Intraday Market-Neutral Statistical Arbitrage",
        "description": """
        Quantitative Alpha - B3 is an institutional-grade, market-neutral statistical arbitrage strategy designed exclusively to exploit behavioral overreactions during the highly volatile market open. Moving away from traditional technical analysis or directional betting, this model relies entirely on Volatility-Adjusted Relative Extremes. The algorithm precisely isolates the overnight price action—the gap between the previous day's close and the current day's open—across the entire IBOV universe. It then divides this raw gap by each specific stock's 20-day historical standard deviation. This critical normalization process converts a simple percentage gap into a rigorous statistical Z-Score, allowing the engine to measure exactly how abnormal a morning gap is relative to that specific asset's historical behavioral baseline.

        At exactly 9:30 AM, the algorithmic engine cross-sectionally ranks the analyzed universe based on these Z-Scores. It then constructs a perfectly balanced, market-neutral portfolio designed to act as a liquidity provider during early morning chaos. The system automatically executes long positions on the most severely suppressed gaps—fading morning retail panic—and simultaneously takes short positions on the most heavily inflated gaps, fading morning euphoria. By anchoring itself to both sides of the market evenly, the strategy entirely neutralizes broader market directional risk (Beta). The portfolio captures pure alpha through intraday mean-reversion as the targeted assets naturally gravitate back toward their fair value by the 4:00 PM market close. With strictly zero overnight exposure, Quantitative Alpha delivers a mathematically pure, non-directional return stream.
        """
    },
    "LAM Strategy": {
        "file": "lam_strategy_logbook.csv",
        "type": "Auto-Adaptive Multi-Model Swing Portfolio",
        "description": """
        The flagship LAM Strategy is a highly advanced, auto-adaptive swing trading portfolio driven by a robust ensemble of seven distinct quantitative models. Designed to navigate and conquer complex, multi-day market cycles, the foundation of this strategy rests heavily on rigorous statistical mathematics rather than conventional charting. The primary engine utilizes the Hurst Exponent to continuously monitor and detect shifting market regimes—accurately distinguishing between trending (persistent) and mean-reverting (anti-persistent) environments. Concurrently, it applies Ornstein-Uhlenbeck processes to calculate mathematically optimal mean-reversion half-lives, dictating exactly how long a swing position should be held.

        Depending on the detected regime, the algorithmic framework dynamically rotates capital across its sub-strategies. These include models targeting extreme Volatility Compression (detecting quiet periods before explosive breakouts), Volume Climaxes (fading institutional exhaustion), adaptive Keltner Squeezes, and Anchored VWAP Divergences. Unlike our strictly intraday models, the LAM Strategy is designed to hold overnight exposure, capturing larger multi-day alpha. To mitigate the inherent risks of swing trading, the framework operates on a rigorous step-forward walking backtest architecture. Risk is managed asymmetrically via dynamic, volatility-adjusted Stop-Loss and Take-Profit brackets, alongside strict volume liquidity minimums to ensure seamless execution. Crucially, the engine features an institutional "Mirror Book" parameter. If macroeconomic headwinds dictate severe structural system decay, the algorithm can seamlessly invert its entire signal logic, allowing the portfolio to remain profitable even when traditional market conditions completely break down.
        """
    },
    "Swing Trade ATR": {
        "file": "swing_atr_logbook.csv",
        "type": "Systematic Scale-In Portfolio Matrix",
        "description": """
        The Swing Trade ATR framework is an institutional-grade, multi-tranche scale-in engine engineered to systematically build positions during extreme pricing anomalies. At its core, the strategy is predicated on the mathematical certainty of mean reversion, utilizing a 20-day Exponential Weighted Moving Average (EWMA) as the fundamental baseline for fair value. Rather than executing a single, rigid entry, the portfolio manager module deploys capital across five calculated tranches, scaling into positions as an asset deviates further from its baseline. 

        To ensure mathematical precision, these scale-in levels are not arbitrary percentages; they are strictly guarded by Average True Range (ATR) volatility bands. As an asset drops 2.0, 3.0, 4.5, 6.0, and ultimately 8.0 ATR multiples below its EWMA, the engine progressively increases its capital allocation weighting. However, to prevent the system from blindly catching "falling knives" during structural market crashes, the strategy employs a rolling 60-day Hurst exponent as an absolute regime filter. If the Hurst calculation indicates a persistent downward trend (a value greater than 0.55), the scale-in logic is instantly aborted. The exit mechanism is equally systematic: the entire aggregate position is closed the moment the asset's price reverts to the rolling EWMA baseline. By combining dynamic volatility mapping, strict maximum gross exposure limits, and advanced regime detection, the Swing Trade ATR strategy offers a mathematically sound approach to capturing aggressive reversion alpha while strictly defining downside risk parameters.
        """
    }
}

# --- 5. APP LAYOUT & NAVIGATION ---
with st.sidebar:
    st.markdown("## LAM Capital")
    st.markdown("Quantitative Asset Management")
    st.markdown("---")
    selected_strategy = st.radio("Select Strategy:", options=list(STRATEGIES.keys()))
    st.markdown("---")
    st.markdown("<small>CONFIDENTIAL PROSPECTUS</small>", unsafe_allow_html=True)

strategy_data = STRATEGIES[selected_strategy]

# Top Bar
col_title, col_btn = st.columns([4, 1])
with col_title:
    st.title(selected_strategy)
    st.markdown(f"**Classification:** {strategy_data['type']}")
with col_btn:
    st.write("") 
    st.download_button(
        label="📄 Download PDF Prospectus",
        data=b"PDF_BYTE_DATA_PLACEHOLDER", 
        file_name=f"LAM_Capital_{selected_strategy.replace(' ', '_')}.pdf",
        mime="application/pdf",
        use_container_width=True
    )

st.markdown("---")
st.markdown("## Strategy Overview")
st.markdown(strategy_data["description"])

# Load Data
raw_df = load_strategy_data(strategy_data["file"])
daily_pnl, days_trading, overall_return, sharpe, max_dd = calculate_metrics(raw_df)

st.markdown("## Risk & Performance Analysis")
st.markdown("<small>Based on $1,000,000 USD Initial Capitalization</small>", unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Cumulative Return", f"{overall_return:,.2f}%")
m2.metric("Sharpe Ratio", f"{sharpe:.2f}")
m3.metric("Maximum Drawdown", f"{max_dd:.2f}%")
m4.metric("Trading Days", f"{days_trading:,}")

st.markdown("---")
st.markdown("## Net Asset Value (NAV) Evolution")
fig = plot_performance(daily_pnl, selected_strategy)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.markdown("## Monthly Return Matrix")
monthly_table = generate_monthly_table(daily_pnl)
st.dataframe(monthly_table, use_container_width=True)

st.markdown("---")
st.markdown("## Trade History")
csv_data = raw_df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="⬇️ Download Raw Execution Log (.csv)",
    data=csv_data,
    file_name=f"{selected_strategy.replace(' ', '_')}_logbook.csv",
    mime="text/csv",
)
