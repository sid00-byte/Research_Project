import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# --- PAGE CONFIG ---
st.set_page_config(page_title="Equity Factor Research Terminal", layout="wide")

# --- DATA LOADING ---
@st.cache_data
def load_data():
    # Looks for data in the 'data' subfolder
    df = pd.read_csv('data/ranked_results.csv')
    df['fiscalDateEnding'] = pd.to_datetime(df['fiscalDateEnding'])
    
    # Ensure 5 perfect quintiles for the chart
    df['rank_quintile'] = df.groupby('fiscalDateEnding')['composite_score'].transform(
        lambda x: pd.qcut(x.rank(method='first'), 5, labels=False)
    )
    return df

df = load_data()
latest_date = df['fiscalDateEnding'].max()

# --- HEADER & METRICS ---
st.title("📈 Equity Factor Research Terminal")
st.markdown(f"**Strategy:** Value + Quality Ranking | **Universe:** US Equities | **As of:** {latest_date.date()}")

# Calculating Overall Alpha Spread
top_ret = df[df['rank_quintile'] == 4]['target_return'].mean()
bot_ret = df[df['rank_quintile'] == 0]['target_return'].mean()
overall_alpha = top_ret - bot_ret

m1, m2, m3 = st.columns(3)
m1.metric("Strategy Alpha (Spread)", f"{overall_alpha:.2%}", delta="Long/Short Edge")
m2.metric("Mean IC", "-0.0129", help="Rank correlation across full history")
m3.metric("Current Universe", f"{len(df[df['fiscalDateEnding'] == latest_date])} Tickers")

st.divider()

# --- VISUALS ---
left, right = st.columns([1.5, 1])

with left:
    st.subheader("Performance by Factor Quintile")
    q_perf = df.groupby('rank_quintile')['target_return'].mean() * 100
    fig = px.bar(
        x=['Q0 (Bottom)', 'Q1', 'Q2', 'Q3', 'Q4 (Top)'],
        y=q_perf.values,
        color=q_perf.values,
        color_continuous_scale='RdYlGn',
        labels={'x': 'Factor Score', 'y': 'Avg. Annual Return (%)'},
        text_auto='.2f'
    )
    fig.update_layout(template="plotly_dark", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("🎯 Current Top 10 Picks")
    latest_picks = df[df['fiscalDateEnding'] == latest_date].sort_values('composite_score', ascending=False).head(10)
    st.dataframe(
        latest_picks[['ticker', 'sector', 'composite_score']],
        column_config={"composite_score": st.column_config.ProgressColumn("Score", min_value=0, max_value=1)},
        hide_index=True
    )
