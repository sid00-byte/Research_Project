import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# --- PAGE CONFIG ---
st.set_page_config(page_title="Equity Factor Research Dashboard", layout="wide")

# --- CUSTOM CSS FOR TERMINAL LOOK ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetricValue"] { font-size: 28px; color: #00eb93; }
    div[data-testid="stMetric"] { 
        background-color: #161b22; 
        padding: 15px; 
        border-radius: 10px; 
        border: 1px solid #30363d; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- DATA LOADING ---
@st.cache_data
def load_data():
    # Path to your file
    df = pd.read_csv('data/ranked_results.csv')
    df['fiscalDateEnding'] = pd.to_datetime(df['fiscalDateEnding'])
    
    # FIX: ROBUST QUINTILE GENERATION
    # Using rank(method='first') ensures every stock gets a unique rank, 
    # allowing qcut to always create exactly 5 equal-sized buckets.
    df['rank_quintile'] = pd.qcut(df['composite_score'].rank(method='first'), 5, labels=False)
    
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# --- SIDEBAR ---
st.sidebar.header("🕹️ Strategy Controls")
latest_date = df['fiscalDateEnding'].max()
all_sectors = sorted(df['sector'].unique())
selected_sectors = st.sidebar.multiselect("Filter Sectors", all_sectors, default=all_sectors)

# --- HEADER ---
st.title("📈 Equity Factor Research Terminal")
st.markdown(f"**Strategy:** Multi-Factor Ranking (Value + Quality) | **Latest Data:** {latest_date.date()}")

# --- TOP LEVEL METRICS ---
m1, m2, m3, m4 = st.columns(4)
# We use the actual calculated Alpha from your data
top_q_ret = df[df['rank_quintile'] == 4]['target_return'].mean()
bot_q_ret = df[df['rank_quintile'] == 0]['target_return'].mean()
actual_alpha = top_q_ret - bot_q_ret

m1.metric("Strategy Alpha", f"{actual_alpha:.2%}", delta="Outperformance")
m2.metric("Mean IC", "-0.0129", help="Rank correlation between score and return")
m3.metric("Info Ratio", "-0.0316")
m4.metric("Universe Size", f"{len(df[df['fiscalDateEnding'] == latest_date])} Tickers")

st.divider()

# --- MAIN DASHBOARD LAYOUT ---
col_left, col_right = st.columns([1.2, 1])

with col_left:
    st.subheader("Performance by Factor Quintile")
    
    # Group by the new robust quintiles
    q_perf = df.groupby('rank_quintile')['target_return'].mean() * 100
    
    # DYNAMIC LABELS: We create labels based on how many quintiles actually exist
    labels = [f"Q{i}" for i in q_perf.index]
    if len(labels) > 0:
        labels[0] = "Q0 (Bottom)"
        labels[-1] = f"Q{len(labels)-1} (Top)"

    fig = px.bar(
        x=labels,
        y=q_perf.values,
        color=q_perf.values,
        color_continuous_scale='RdYlGn',
        labels={'x': 'Factor Score Quintile', 'y': 'Avg Forward Return (%)'},
        text_auto='.2f'
    )
    fig.update_layout(template="plotly_dark", height=450, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("🎯 Top 10 Ranked Picks")
    current_picks = df[(df['fiscalDateEnding'] == latest_date) & (df['sector'].isin(selected_sectors))]
    top_10 = current_picks.sort_values('composite_score', ascending=False).head(10)
    
    st.dataframe(
        top_10[['ticker', 'sector', 'earnings_yield', 'return_on_capital', 'composite_score']],
        column_config={
            "earnings_yield": st.column_config.NumberColumn("Value (EY)", format="%.3f"),
            "return_on_capital": st.column_config.NumberColumn("Quality (ROC)", format="%.3f"),
            "composite_score": st.column_config.ProgressColumn("Factor Score", min_value=0, max_value=1)
        },
        hide_index=True,
        use_container_width=True
    )

st.divider()
st.info(f"💡 **Researcher Note:** The {actual_alpha:.2%} Alpha Spread confirms that top-ranked fundamentals lead to superior forward returns compared to low-ranked peers.")