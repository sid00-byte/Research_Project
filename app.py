import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# --- PAGE CONFIG ---
st.set_page_config(page_title="Equity Factor Research Terminal", layout="wide")

# --- 1. BULLETPROOF DATA LOADING ---
@st.cache_data
def load_data():
    # Load the data
    df = pd.read_csv('data/ranked_results.csv')
    df['fiscalDateEnding'] = pd.to_datetime(df['fiscalDateEnding'])
    
    # ROBUST QUINTILE LOGIC:
    # Instead of qcut (which crashes on small groups), we use percentile ranking.
    def calculate_robust_quintiles(group):
        if len(group) == 0:
            return group
        # Rank from 0 to 1
        pct_ranks = group.rank(method='first', pct=True)
        # Map 0.0-1.0 to integers 0, 1, 2, 3, 4
        return (pct_ranks * 4.99).astype(int)

    df['rank_quintile'] = df.groupby('fiscalDateEnding')['composite_score'].transform(calculate_robust_quintiles)
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

latest_date = df['fiscalDateEnding'].max()

# --- 2. HEADER & METRICS ---
st.title("📈 Equity Factor Research Terminal")
st.markdown(f"**Strategy:** Value + Quality Ranking | **Universe:** US Equities | **As of:** {latest_date.date()}")

# Calculate Strategy Alpha (Top vs Bottom Quintile)
top_ret = df[df['rank_quintile'] == 4]['target_return'].mean()
bot_ret = df[df['rank_quintile'] == 0]['target_return'].mean()
overall_alpha = top_ret - bot_ret

m1, m2, m3 = st.columns(3)
# Note: This displays the +2.35% Spread we found in your research
m1.metric("Strategy Alpha (Spread)", f"{overall_alpha:.2%}", delta="Long/Short Edge")
m2.metric("Mean IC", "-0.0129", help="Rank correlation across full history")
m3.metric("Current Universe", f"{len(df[df['fiscalDateEnding'] == latest_date])} Tickers")

st.divider()

# --- 3. VISUALS ---
left, right = st.columns([1.5, 1])

with left:
    st.subheader("Performance by Factor Quintile")
    # Group and calculate mean returns
    q_perf = df.groupby('rank_quintile')['target_return'].mean() * 100
    
    # Ensure chart labels match the data points present
    all_labels = ['Q0 (Bottom)', 'Q1', 'Q2', 'Q3', 'Q4 (Top)']
    current_labels = [all_labels[int(i)] for i in q_perf.index]
    
    fig = px.bar(
        x=current_labels,
        y=q_perf.values,
        color=q_perf.values,
        color_continuous_scale='RdYlGn',
        labels={'x': 'Factor Score Quintile', 'y': 'Avg. Annual Return (%)'},
        text_auto='.2f'
    )
    fig.update_layout(template="plotly_dark", showlegend=False, height=450)
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("🎯 Current Top 10 Picks")
    # Show the best stocks for the most recent date
    latest_picks = df[df['fiscalDateEnding'] == latest_date].sort_values('composite_score', ascending=False).head(10)
    st.dataframe(
        latest_picks[['ticker', 'sector', 'composite_score']],
        column_config={
            "composite_score": st.column_config.ProgressColumn("Factor Score", min_value=0, max_value=1)
        },
        hide_index=True,
        use_container_width=True
    )

st.info("💡 **Researcher Note:** Even with negative alpha in individual crisis years (like 2008), the long-term aggregate spread remains positive at +2.35%.")
