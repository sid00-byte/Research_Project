import pandas as pd
import glob
import os

# 1. Path to your folder containing all ticker CSVs
path = '/Users/siddharth/Research_Project/'

all_files = glob.glob(os.path.join(path, "*.csv"))

# Define all columns from your image EXCEPT 'sector'
cols_to_import = [
    'ticker','sector','fiscalDateEnding', 'price_date_start', 'price_start', 
    'price_end', 'pe_ratio', 'earnings_yield', 'return_on_capital', 
    'debt_ratio', 'debt_to_equity', 'current_ratio', 'profit_margin', 
    'asset_turnover', 'book_to_market', 'rev_growth', 'ebit_growth', 
    'target_return'
]

li = []

for filename in all_files:
    # Read only the relevant columns directly
    df_temp = pd.read_csv(filename, usecols=cols_to_import)
    
    # Convert date to datetime to ensure proper chronological sorting
    df_temp['fiscalDateEnding'] = pd.to_datetime(df_temp['fiscalDateEnding'])
    
    li.append(df_temp)

# 2. Stack all tickers into one master dataframe
df_master = pd.concat(li, axis=0, ignore_index=True)

# 3. Final Sort: Essential for time-series integrity
# This ensures that for every ticker, data flows from 2006 up to 2024
df_master = df_master.sort_values(['ticker', 'fiscalDateEnding'])

# 4. Save the collated training set
df_master.to_csv('xgb_ready.csv', index=False)

print(f"Collation complete. Total rows: {len(df_master)}")