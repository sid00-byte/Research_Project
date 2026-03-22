import pandas as pd
import numpy as np
import warnings

# Suppress warnings for cleaner GitHub-ready output
warnings.filterwarnings('ignore', category=RuntimeWarning)
warnings.filterwarnings('ignore', category=FutureWarning)

# 1. Load the data
try:
    df = pd.read_csv('data/ranked_results.csv')
    # Convert date to datetime to ensure proper sorting
    df['fiscalDateEnding'] = pd.to_datetime(df['fiscalDateEnding'])
except FileNotFoundError:
    print("❌ Error: data/ranked_results.csv not found. Run factor_ranking.py first.")
    exit()

# 2. Re-calculate Rankings & Quintiles by Date (Cross-Sectional Integrity)
# We do this here to ensure Step 4 metrics are 100% accurate
def get_metrics_ready(group):
    # Standardize ranks within the date
    group['val_rank'] = group['earnings_yield'].rank(pct=True, method='first')
    group['qual_rank'] = group['return_on_capital'].rank(pct=True, method='first')
    group['score'] = (group['val_rank'] + group['qual_rank']) / 2
    
    # Create quintiles (0-4)
    if len(group) >= 5:
        group['quintile'] = pd.qcut(group['score'], 5, labels=False, duplicates='drop')
    else:
        group['quintile'] = np.nan
    return group

df = df.groupby('fiscalDateEnding').apply(get_metrics_ready).reset_index(drop=True)

# 3. Calculate Information Coefficient (IC)
def calculate_ic(group):
    if len(group) < 5 or group['target_return'].std() == 0:
        return np.nan
    return group['score'].corr(group['target_return'], method='spearman')

ic_series = df.groupby('fiscalDateEnding').apply(calculate_ic).dropna()

# 4. Calculate Final Metrics
mean_ic = ic_series.mean()
ir = mean_ic / ic_series.std() if ic_series.std() > 0 else 0

# Calculate Average Return per Quintile (Handles the NaN issue)
# We take the mean return for all stocks in group 4 vs group 0
top_q_return = df[df['quintile'] == 4]['target_return'].mean()
bot_q_return = df[df['quintile'] == 0]['target_return'].mean()
alpha_spread = top_q_return - bot_q_return

# 5. Professional Output
print("\n" + "="*45)
print("   STEP 4: QUANTITATIVE RESEARCH METRICS")
print("="*45)
print(f"{'Metric':<30} | {'Value':<10}")
print("-"*45)
print(f"{'Information Coefficient (IC)':<30} | {mean_ic:.4f}")
print(f"{'Information Ratio (IR)':<30} | {ir:.4f}")

if not np.isnan(alpha_spread):
    print(f"{'Strategy Alpha (Spread)':<30} | {alpha_spread:.2%}")
else:
    print(f"{'Strategy Alpha (Spread)':<30} | Insufficient Data")

print("-"*45)
print("Note: IC measures signal strength. IR measures consistency.")
print("A spread > 0 indicates factor outperformance.")
print("="*45 + "\n")