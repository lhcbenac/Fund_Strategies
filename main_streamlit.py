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
        
        @media print {
            section[data-testid="stSidebar"] { display: none !important; }
            header[data-testid="stHeader"] { display: none !important; }
            .stDownloadButton, .print-btn-container { display: none !important; }
            .block-container { max-width: 100% !important; padding: 0 !important; }
            @page { margin: 1cm; size: A4 portrait; }
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. GLOBAL CONSTANTS ---
INITIAL_INVESTMENT = 1000000.0  
ANNUAL_BENCHMARK = 0.10 
DAILY_BENCHMARK = ANNUAL_BENCHMARK / 252

# --- 3. DATA ENGINE ---
@st.cache_data
def load_data(filename: str):
    if not os.path.exists(filename):
        return None
    try:
        df = pd.read_csv(filename)
        # Compatibility Layer: Map Loop_Date to Date if needed
        if 'Loop_Date' in df.columns and 'Date' not in df.columns:
            df.rename(columns={'Loop_Date': 'Date'}, inplace=True)
        
        df['Date'] = pd.to_datetime(df['Date'])
        return df.sort_values('Date').reset_index(drop=True)
    except Exception:
        return None

def calculate_kpis(df: pd.DataFrame):
    daily = df.groupby(df['Date'].dt.date)['PNL'].sum().reset_index()
    daily['Date'] = pd.to_datetime(daily['Date'])
    daily['Cumulative_PNL'] = daily['PNL'].cumsum()
    daily['NAV'] = INITIAL_INVESTMENT + daily['Cumulative_PNL']
    daily['Strat_Cum_Ret'] = (daily['Cumulative_PNL'] / INITIAL_INVESTMENT) * 100
    daily['Bench_Cum_Ret'] = ((1 + DAILY_BENCHMARK) ** np.arange(1, len(daily) + 1) - 1) * 100
    
    monthly_pnl = daily.groupby(daily['Date'].dt.to_period('M'))['PNL'].sum()
    total_ret = daily['Strat_Cum_Ret'].iloc[-1]
    bench_ret = daily['Bench_Cum_Ret'].iloc[-1]
    
    rolling_max = daily['NAV'].cummax()
    max_dd = (((daily['NAV'] - rolling_max) / rolling_max) * 100).min()
    
    return daily, total_ret, (total_ret/bench_ret*100), (monthly_pnl > 0).sum(), (monthly_pnl < 0).sum(), max_dd, (monthly_pnl.max()/INITIAL_INVESTMENT*100), (monthly_pnl.min()/INITIAL_INVESTMENT*100)

# --- 4. STRATEGY REPOSITORY ---
STRATEGIES = {
    "Olho Diário": {
        "file": "olho_logbook.csv",
        "type": "Intraday Quantitative Equity Portfolio",
        "liq": "T+0", "audience": "Qualified", "fee": "2.0/20",
        "desc": "Olho Diário is a sophisticated intraday engine engineered to capitalize on immediate market momentum and gap imbalances. By stressing 2,000 scenarios per asset daily, the model selects the top 20 equities for execution. With zero overnight exposure, the strategy provides a powerful buffer against macroeconomic volatility."
    },
    "Quantitative Alpha - B3": {
        "file": "market_neutral_logbook.csv",
        "type": "Intraday Market-Neutral Arbitrage",
        "liq": "T+0", "audience": "Professional", "fee": "2.0/20",
        "desc": "This strategy exploits behavioral overreactions at the market open. Using Volatility-Adjusted Z-Scores, it builds a perfectly balanced 5 Long / 5 Short book to capture intraday mean-reversion with zero market beta."
    }
}

# --- 5. UI ---
with st.sidebar:
    st.markdown("## LAM CAPITAL")
    selected_strategy = st.radio("Factsheet Selector:", options=list(STRATEGIES.keys()))
    strat_meta = STRATEGIES[selected_strategy]

raw_df = load_data(strat_meta["file"])

if raw_df is None:
    st.info(f"System Synchronizing: `{strat_meta['file']}` not found.")
    st.stop()

daily_df, total_ret, pct_bench, pos_m, neg_m, max_dd, max_m, min_m = calculate_kpis(raw_df)

col_t, col_a = st.columns([2.5, 1])
with col_t:
    st.markdown(f"<h1>{selected_strategy}</h1><h3>{strat_meta['type']}</h3>", unsafe_allow_html=True)
with col_a:
    st.write(""); st.write("")
    components.html('<button onclick="window.parent.print()" style="width:100%; padding:10px; background:#1c3c54; color:white; border:none; border-radius:4px; cursor:pointer;">🖨️ Print to PDF</button>', height=50)
    st.download_button("⬇️ Export Ledger", raw_df.to_csv(index=False), strat_meta["file"], "text/csv", use_container_width=True)

st.markdown(f"<p>{strat_meta['desc']}</p>", unsafe_allow_html=True)

# Chart
fig = go.Figure()
fig.add_trace(go.Scatter(x=daily_df['Date'], y=daily_df['Bench_Cum_Ret'], name='Benchmark', line=dict(color='#86868b', dash='dot')))
fig.add_trace(go.Scatter(x=daily_df['Date'], y=daily_df['Strat_Cum_Ret'], name='Strategy', line=dict(color='#0071e3', width=3), fill='tozeroy'))
fig.update_layout(height=400, template="white", margin=dict(l=0,r=0,t=10,b=0), legend=dict(orientation="h", y=1.1))
st.plotly_chart(fig, use_container_width=True)

# Tables
c1, _, c2 = st.columns([1, 0.1, 1])
with c1:
    st.markdown(f"""<h2>Performance Metrics</h2><table class='info-table'>
        <tr><th>Total Return</th><td>{total_ret:.2f}%</td></tr>
        <tr><th>vs Benchmark</th><td>{pct_bench:.2f}%</td></tr>
        <tr><th>Max Drawdown</th><td>{max_dd:.2f}%</td></tr>
        <tr><th>Positive Months</th><td>{pos_m}</td></tr></table>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<h2>General Info</h2><table class='info-table'>
        <tr><th>Liquidity</th><td>{strat_meta['liq']}</td></tr>
        <tr><th>Min. Investment</th><td>$ 1,000,000</td></tr>
        <tr><th>Fees</th><td>{strat_meta['fee']}</td></tr>
        <tr><th>Audience</th><td>{strat_meta['audience']}</td></tr></table>""", unsafe_allow_html=True)
