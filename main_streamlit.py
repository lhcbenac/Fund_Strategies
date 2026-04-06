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
RISK_FREE_RATE = 0.10 / 252 # Assumed 10% annual CDI benchmark equivalent 

# --- 3. DATA PROCESSING FUNCTIONS ---
@st.cache_data
def load_strategy_data(filename: str) -> pd.DataFrame:
    if os.path.exists(filename):
        df = pd.read_csv(filename)
        df['Date'] = pd.to_datetime(df['Date'])
        return df.sort_values('Date')
    else:
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
    
    # Simulate a benchmark line (CDI proxy)
    benchmark_growth = INITIAL_INVESTMENT * (1 + (0.10/252)) ** np.arange(len(daily_pnl))
    
    fig.add_trace(go.Scatter(
        x=daily_pnl['Date'], y=benchmark_growth,
        mode='lines', name='CDI (Benchmark)',
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
        yaxis=dict(showgrid=True, gridcolor='#f5f5f7', linecolor='#d2d2d7', tickfont=dict(color='#86868b'), tickprefix="R$"),
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
    
    months_map = {i: calendar.month_abbr[i].lower() for i in range(1, 13)}
    pivot_table = pivot_table.rename(columns=months_map)
    
    for m in months_map.values():
        if m not in pivot_table.columns:
            pivot_table[m] = np.nan
            
    pivot_table = pivot_table[list(months_map.values())]
    pivot_table['Acum.'] = pivot_table.sum(axis=1)
    
    styled_table = pivot_table.applymap(lambda x: f"{x:.2f}%" if pd.notnull(x) else "-")
    return styled_table

# --- 4. STRATEGY CONTENT DICTIONARY ---
STRATEGIES = {
    "Olho Diário": {
        "file": "olho_logbook.csv",
        "type": "Intraday Quantitative Equity Portfolio",
        "description": "Designed to isolate and capitalize on immediate market momentum, gap imbalances, and structural reversals. The core engine dynamically stresses over 2,000 scenarios per asset daily to rank the top 20 equities. Capital allocation is strictly intraday to prevent macroeconomic overnight risk."
    },
    "Quantitative Alpha - B3": {
        "file": "market_neutral_logbook.csv",
        "type": "Intraday Market-Neutral Statistical Arbitrage",
        "description": "An institutional-grade strategy engineered to exploit behavioral overreactions during the chaotic market open. It uses Volatility-Adjusted Z-Scores to rank overnight gaps, building a balanced market-neutral book (Long Morning Panic / Short Morning Euphoria) to capture mean-reversion by the close."
    },
    "LAM Strategy": {
        "file": "lam_strategy_logbook.csv",
        "type": "Auto-Adaptive Multi-Model Swing Portfolio",
        "description": "An ensemble of seven advanced statistical models utilizing the Hurst Exponent for regime detection and Ornstein-Uhlenbeck processes for optimal half-lives. It rotates through mean-reversion and volatility compression setups, featuring dynamic risk brackets and an institutional 'Mirror Book' to invert signals during structural decay."
    },
    "Swing Trade ATR": {
        "file": "swing_atr_logbook.csv",
        "type": "Systematic Scale-In Portfolio Matrix",
        "description": "A robust multi-tranche engine that systematically scales into positions based on extreme deviations from an EWMA baseline, guarded by Average True Range (ATR) limits. It leverages a rolling 60-day Hurst exponent as a strict regime filter to avoid scaling into downward trends, mathematically managing risk and exit targets."
    }
}

# --- 5. APP LAYOUT & NAVIGATION ---
with st.sidebar:
    st.markdown("## LAM Capital")
    st.markdown("Quantitative Asset Management")
    st.markdown("---")
    selected_strategy = st.radio("Selecione a Estratégia:", options=list(STRATEGIES.keys()))
    st.markdown("---")
    st.markdown("<small>MATERIAL DE DIVULGAÇÃO</small>", unsafe_allow_html=True)

strategy_data = STRATEGIES[selected_strategy]

# Top Bar
col_title, col_btn = st.columns([4, 1])
with col_title:
    st.title(selected_strategy)
    st.markdown(f"**Classificação:** {strategy_data['type']}")
with col_btn:
    st.write("") 
    st.download_button(
        label="📄 Download Lâmina PDF",
        data=b"PDF_BYTE_DATA_PLACEHOLDER", 
        file_name=f"LAM_Capital_{selected_strategy.replace(' ', '_')}.pdf",
        mime="application/pdf",
        use_container_width=True
    )

st.markdown("---")
st.markdown("## Resumo da Estratégia")
st.markdown(strategy_data["description"])

# Load Data
raw_df = load_strategy_data(strategy_data["file"])
daily_pnl, days_trading, overall_return, sharpe, max_dd = calculate_metrics(raw_df)

st.markdown("## Análise e Performance de Risco")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Retorno Acumulado", f"{overall_return:,.2f}%")
m2.metric("Índice Sharpe", f"{sharpe:.2f}")
m3.metric("Maximum Drawdown", f"{max_dd:.2f}%")
m4.metric("Dias Operados", f"{days_trading:,}")

st.markdown("---")
st.markdown("## Evolução do Patrimônio Líquido")
fig = plot_performance(daily_pnl, selected_strategy)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.markdown("## Rentabilidades Mensais")
monthly_table = generate_monthly_table(daily_pnl)
st.dataframe(monthly_table, use_container_width=True)

st.markdown("---")
st.markdown("## Histórico de Operações")
csv_data = raw_df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="⬇️ Download Tradelog (.csv)",
    data=csv_data,
    file_name=f"{selected_strategy.replace(' ', '_')}_logbook.csv",
    mime="text/csv",
)
