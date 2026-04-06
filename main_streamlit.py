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

# Institutional CSS & Print Media Queries
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

# --- 2. GLOBAL CONSTANTS ---
INITIAL_INVESTMENT = 1000000.0  
ANNUAL_BENCHMARK_RATE = 0.10 
DAILY_BENCHMARK_RATE = ANNUAL_BENCHMARK_RATE / 252

# --- 3. DATA ENGINE ---
@st.cache_data
def load_data(filename: str):
    if not os.path.exists(filename):
        return None
    try:
        df = pd.read_csv(filename)
        # Compatibility Layer: Map Loop_Date to Date automatically
        if 'Loop_Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Loop_Date'])
        elif 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
        else:
            return None
            
        return df.sort_values('Date').reset_index(drop=True)
    except Exception:
        return None

def calculate_kpis(df: pd.DataFrame):
    # Aggregating all trades per day to get clean Daily PNL
    daily = df.groupby(df['Date'].dt.date)['PNL'].sum().reset_index()
    daily['Date'] = pd.to_datetime(daily['Date'])
    
    daily['Cumulative_PNL'] = daily['PNL'].cumsum()
    daily['NAV'] = INITIAL_INVESTMENT + daily['Cumulative_PNL']
    
    daily['Strat_Cum_Ret'] = (daily['Cumulative_PNL'] / INITIAL_INVESTMENT) * 100
    daily['Bench_Cum_Ret'] = ((1 + DAILY_BENCHMARK_RATE) ** np.arange(1, len(daily) + 1) - 1) * 100
    
    daily['YearMonth'] = daily['Date'].dt.to_period('M')
    monthly_returns = daily.groupby('YearMonth')['PNL'].sum()
    
    total_ret = daily['Strat_Cum_Ret'].iloc[-1] if not daily.empty else 0
    bench_ret = daily['Bench_Cum_Ret'].iloc[-1] if not daily.empty else 0
    pct_bench = (total_ret / bench_ret) * 100 if bench_ret != 0 else 0
    
    rolling_max = daily['NAV'].cummax()
    max_dd = (((daily['NAV'] - rolling_max) / rolling_max) * 100).min()
    
    return daily, total_ret, pct_bench, (monthly_returns > 0).sum(), (monthly_returns < 0).sum(), max_dd, (monthly_returns.max()/INITIAL_INVESTMENT*100), (monthly_returns.min()/INITIAL_INVESTMENT*100)

# --- 4. STRATEGY REPOSITORY ---
STRATEGIES = {
    "Olho Diário": {
        "file": "olho_logbook.csv",
        "type": "Intraday Quantitative Equity Portfolio",
        "audience": "Qualified Investors",
        "fee": "2.00% p.a. | 20% > Benchmark",
        "desc": "The Olho Diário strategy is a sophisticated intraday quantitative equity portfolio engineered to isolate and capitalize on immediate market momentum, gap imbalances, and structural price reversals. It continuously retrains its model using OHLC data and current-day opening auction values to identify forward-looking, highly profitable entry routes. By ensuring all positions are closed within the same session, it maintains zero overnight exposure."
    },
    "Quantitative Alpha - B3": {
        "file": "market_neutral_logbook.csv",
        "type": "Intraday Market-Neutral Statistical Arbitrage",
        "audience": "Professional Investors",
        "fee": "2.00% p.a. | 20% > Benchmark",
        "desc": "Quantitative Alpha - B3 is an institutional-grade, market-neutral framework designed to exploit behavioral overreactions at the market open. Using Volatility-Adjusted Z-Scores, it identifies extreme panic or euphoria gaps and builds a perfectly balanced 5-Long/5-Short book, capturing intraday mean-reversion with zero market beta."
    },
    "LAM Strategy": {
        "file": "lam_strategy_logbook.csv",
        "type": "Auto-Adaptive Multi-Model Swing Portfolio",
        "audience": "Qualified Investors",
        "fee": "2.00% p.a. | 20% > Benchmark",
        "desc": "A swing trading portfolio driven by an ensemble of seven distinct models. It utilizes the Hurst Exponent for regime detection and Ornstein-Uhlenbeck processes for half-life calculation, rotating capital across mean-reversion and volatility compression strategies."
    },
    "Swing Trade ATR": {
        "file": "swing_atr_logbook.csv",
        "type": "Systematic Scale-In Portfolio Matrix",
        "audience": "Qualified Investors",
        "fee": "1.50% p.a. | 20% > Benchmark",
        "desc": "A multi-tranche engine that systematically scales into positions based on deviations from an EWMA baseline, guarded by ATR volatility bands and regime filters."
    }
}

# --- 5. UI LAYOUT ---
with st.sidebar:
    st.markdown("## LAM CAPITAL")
    selected_strategy = st.radio("Select Strategy:", options=list(STRATEGIES.keys()))
    strat_meta = STRATEGIES[selected_strategy]

raw_df = load_data(strat_meta["file"])

if raw_df is None:
    st.info(f"**System Notice:** Expected file `{strat_meta['file']}` not found in repository.")
    st.stop()

daily_df, total_ret, pct_bench, pos_m, neg_m, max_dd, max_m, min_m = calculate_kpis(raw_df)

# Header Section
col_t, col_a = st.columns([2.5, 1])
with col_t:
    st.markdown(f"<h1>{selected_strategy}</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='margin-top:-5px;'>{strat_meta['type']}</h3>", unsafe_allow_html=True)
with col_a:
    st.write("")
    components.html('<button onclick="window.parent.print()" style="width:100%; padding:10px; background:#1c3c54; color:white; border:none; border-radius:4px; cursor:pointer; font-weight:600;">🖨️ Print to PDF</button>', height=50)
    st.download_button("⬇️ Export Ledger (.csv)", raw_df.to_csv(index=False), strat_meta["file"], "text/csv", use_container_width=True)

# Narrative
st.markdown(f"<p>{strat_meta['desc']}</p>", unsafe_allow_html=True)

# Chart
fig = go.Figure()
fig.add_trace(go.Scatter(x=daily_df['Date'], y=daily_df['Bench_Cum_Ret'], name='Benchmark', line=dict(color='#86868b', dash='dot')))
fig.add_trace(go.Scatter(x=daily_df['Date'], y=daily_df['Strat_Cum_Ret'], name=selected_strategy, line=dict(color='#0071e3', width=3), fill='tonexty', fillcolor='rgba(0, 113, 227, 0.08)'))
fig.update_layout(height=450, template="white", margin=dict(l=0,r=0,t=10,b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
st.plotly_chart(fig, use_container_width=True)

# Matrix Logic
st.markdown("<h2>Monthly Return Matrix</h2>", unsafe_allow_html=True)
df_m = daily_df.copy()
df_m['Year'] = df_m['Date'].dt.year
df_m['Month'] = df_m['Date'].dt.month
matrix = (df_m.groupby(['Year', 'Month'])['PNL'].sum() / INITIAL_INVESTMENT * 100).unstack()
matrix.columns = [calendar.month_name[m][:3] for m in matrix.columns]
matrix['YTD'] = matrix.sum(axis=1)
st.dataframe(matrix.style.format("{:.2f}%", na_rep="-"), use_container_width=True)

# Metrics Grid
c1, _, c2 = st.columns([1, 0.1, 1])
with c1:
    st.markdown(f"""<h2>Risk & Performance Metrics</h2><table class="info-table">
        <tr><th>Total Return</th><td>{total_ret:.2f}%</td></tr>
        <tr><th>vs Benchmark</th><td>{pct_bench:.2f}%</td></tr>
        <tr><th>Positive Months</th><td>{pos_m}</td></tr>
        <tr><th>Max Drawdown</th><td>{max_dd:.2f}%</td></tr>
    </table>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<h2>General Information</h2><table class="info-table">
        <tr><th>Target Audience</th><td>{strat_meta['audience']}</td></tr>
        <tr><th>Fees</th><td>{strat_meta['fee']}</td></tr>
        <tr><th>Redemption Liquidity</th><td>T+30</td></tr>
        <tr><th>Initial Allocation</th><td>$ 1,000,000</td></tr>
    </table>""", unsafe_allow_html=True)
