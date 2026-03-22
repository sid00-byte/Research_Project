import pandas as pd
import os
import numpy as np

# --- 1. SETUP DIRECTORIES ---
INPUT_FILE = 'xgb_ready.csv'
OUTPUT_DIR = 'data'
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'ranked_results.csv')

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
    print(f"✅ Created directory: {OUTPUT_DIR}")

# --- 2. LOAD DATA ---
try:
    df = pd.read_csv(INPUT_FILE)
    print(f"✅ Successfully loaded {INPUT_FILE}")
except FileNotFoundError:
    print(f"❌ Error: {INPUT_FILE} not found. Please ensure it is in the same folder as this script.")
    exit()

# --- 3. SECTOR-NEUTRAL RANKING LOGIC ---
print("📊 Calculating Sector-Neutral Ranks...")

# Rank Earnings Yield (Value) and ROC (Quality) within each Date and Sector
# method='first' ensures unique ranks even with tied data
df['val_rank'] = df.groupby(['fiscalDateEnding', 'sector'])['earnings_yield'].rank(pct=True, method='first')
df['qual_rank'] = df.groupby(['fiscalDateEnding', 'sector'])['return_on_capital'].rank(pct=True, method='first')

# Composite Score: Combine the two factors (0.0 to 1.0 scale)
df['composite_score'] = (df['val_rank'] + df['qual_rank']) / 2

# --- 4. QUINTILE ANALYSIS (The NaN Fix) ---
# We use 5 buckets (Quintiles) instead of 10 (Deciles) because the universe size
# is small. This ensures every bucket has enough stocks for an average return.
try:
    df['rank_quintile'] = pd.qcut(df['composite_score'], q=5, labels=False, duplicates='drop')
    top_group = df['rank_quintile'].max()
except ValueError:
    df['rank_quintile'] = 0
    top_group = 0

# --- 5. PERFORMANCE METRICS ---
universe_avg = df['target_return'].mean()
top_return = df[df['rank_quintile'] == top_group]['target_return'].mean()
bottom_return = df[df['rank_quintile'] == 0]['target_return'].mean()

# Handle display logic for the console
top_display = f"{top_return:.2%}" if not np.isnan(top_return) else "N/A"
bottom_display = f"{bottom_return:.2%}" if not np.isnan(bottom_return) else "N/A"

print("\n--- Strategy Performance (Quintiles) ---")
print(f"Universe Avg Return:    {universe_avg:.2%}")
print(f"Top 20% Group Return:   {top_display}")
print(f"Bottom 20% Group Return: {bottom_display}")

if not np.isnan(top_return) and not np.isnan(bottom_return):
    print(f"Strategy Spread (Alpha): {top_return - bottom_return:.2%}")

# --- 6. SAVE & EXPORT ---
df.to_csv(OUTPUT_FILE, index=False)
print(f"\n✅ Success! Ranked results saved to: {OUTPUT_FILE}")

# --- 7. LATEST RECOMMENDATIONS ---
latest_date = df['fiscalDateEnding'].max()
top_picks = df[df['fiscalDateEnding'] == latest_date].sort_values('composite_score', ascending=False).head(5)

print(f"\n--- Top 5 Ranked Picks (Latest Data: {latest_date}) ---")
print(top_picks[['ticker', 'sector', 'composite_score']])