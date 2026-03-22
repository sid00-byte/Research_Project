import requests
import pandas as pd
import numpy as np
import time
import os

# --- CONFIGURATION ---
API_KEY = 'M2BJ7CA3HOMM3G04'
BASE_URL = 'https://www.alphavantage.co/query'
TICKERS = ['G', 'EFX', 'VRSK', 'ATGE', 'GHC']
OUTPUT_FILE = 'G_EFX_VRSK_ATGE_GHC.csv'

def prepare_point_in_time_dataset(income_json, balance_json, overview_json, price_json):
    try:
        if 'annualReports' not in income_json or 'annualReports' not in balance_json:
            return None
        
        df_income = pd.DataFrame(income_json['annualReports'])
        df_balance = pd.DataFrame(balance_json['annualReports'])
        
        # IMPROVEMENT: Added Share and Debt columns to raw_cols to ensure they are numeric
        raw_cols = ['totalRevenue', 'ebit', 'netIncome', 'totalAssets', 
                    'totalLiabilities', 'totalShareholderEquity', 
                    'totalCurrentAssets', 'totalCurrentLiabilities',
                    'commonStockSharesOutstanding', 'shortTermDebt', 'longTermDebt',
                    'cashAndCashEquivalentsAtCarryingValue']
        
        for df in [df_income, df_balance]:
            for col in raw_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            df['fiscalDateEnding'] = pd.to_datetime(df['fiscalDateEnding'])

        # Merge on fiscalDateEnding ensures 2010 Income matches 2010 Balance Sheet
        df_funds = pd.merge(df_income, df_balance, on=['fiscalDateEnding'], suffixes=('', '_bs'))
        
        # Metadata
        df_funds['ticker'] = overview_json.get('Symbol', 'UNKNOWN')
        df_funds['sector'] = overview_json.get('Sector', 'Unknown')
        
        # IMPROVEMENT: Use historical shares from Balance Sheet, NOT static Overview shares
        # This prevents "Dilution Bias" where old earnings are divided by new share counts
        df_funds['shares_hist'] = df_funds['commonStockSharesOutstanding']

        # 1. Feature Engineering
        df_funds = df_funds.sort_values('fiscalDateEnding')
        df_funds['rev_growth'] = df_funds['totalRevenue'].pct_change()
        df_funds['ebit_growth'] = df_funds['ebit'].pct_change()
        df_funds['profit_margin'] = df_funds['netIncome'] / df_funds['totalRevenue'].replace(0, np.nan)
        df_funds['current_ratio'] = df_funds['totalCurrentAssets'] / df_funds['totalCurrentLiabilities'].replace(0, np.nan)
        df_funds['debt_to_equity'] = df_funds['totalLiabilities'] / df_funds['totalShareholderEquity'].replace(0, np.nan)
        df_funds['debt_ratio'] = df_funds['totalLiabilities'] / df_funds['totalAssets']
        df_funds['asset_turnover'] = df_funds['totalRevenue'] / df_funds['totalAssets'].replace(0, np.nan)
        df_funds['return_on_capital'] = df_funds['ebit'] / ((df_funds['totalAssets'] - df_funds['totalCurrentLiabilities']-df_funds['cashAndCashEquivalentsAtCarryingValue']).replace(0, np.nan))
        
        # 2. Point-in-Time Lag (90 days) - This is your "Anti-Cheat" shield
        df_funds['data_available_date'] = df_funds['fiscalDateEnding'] + pd.Timedelta(days=90)
        
        if 'Monthly Adjusted Time Series' not in price_json:
            return None
            
        price_data = []
        for date, values in price_json['Monthly Adjusted Time Series'].items():
            price_data.append({'date': pd.to_datetime(date), 'adj_close': float(values['5. adjusted close'])})
        df_prices = pd.DataFrame(price_data).sort_values('date')

        # Join Price Start
        df_funds = pd.merge_asof(df_funds.sort_values('data_available_date'), df_prices, 
                                 left_on='data_available_date', right_on='date', direction='forward')
        df_funds = df_funds.rename(columns={'adj_close': 'price_start', 'date': 'price_date_start'})

        # Join Price End (1 year later)
        df_funds['target_lookup_date'] = df_funds['price_date_start'] + pd.Timedelta(days=365)
        df_funds = pd.merge_asof(df_funds.sort_values('target_lookup_date'), df_prices, 
                                 left_on='target_lookup_date', right_on='date', direction='forward')
        df_funds = df_funds.rename(columns={'adj_close': 'price_end', 'date': 'price_date_end'})

        # 3. Final Calculations
        df_funds['target_return'] = (df_funds['price_end'] - df_funds['price_start']) / df_funds['price_start']
        
        # IMPROVEMENT: BIAS-FREE TRAILING P/E calculation
        # Uses historical shares. Added a 'clip' for negative earnings to prevent model confusion.
        df_funds['eps_hist'] = df_funds['netIncome'] / df_funds['shares_hist']
        df_funds['pe_ratio'] = df_funds['price_start'] / df_funds['eps_hist']
        df_funds['pe_ratio'] = df_funds['pe_ratio'].apply(lambda x: x if x > 0 else 200) # 200 = Loss-making/Expensive

        # IMPROVEMENT: Added Earnings Yield (Inverse P/E based on Enterprise Value)
        # This is the ACTUAL Magic Formula metric.
        df_funds['market_cap'] = df_funds['price_start'] * df_funds['shares_hist']
        df_funds['total_debt'] = df_funds['shortTermDebt'] + df_funds['longTermDebt']
        df_funds['ev'] = (df_funds['market_cap'] + df_funds['total_debt'] - df_funds['cashAndCashEquivalentsAtCarryingValue']).apply(lambda x: x if x > 0 else 0.01)
        df_funds['earnings_yield'] = df_funds['ebit'] / df_funds['ev']

        # Book to Market (Fixed to use historical shares)
        df_funds['book_to_market'] = df_funds['totalShareholderEquity'] / (df_funds['price_start'] * df_funds['shares_hist'])

        # --- UPDATED COLUMN SELECTION ---
        final_columns = [
            'ticker', 'sector', 'fiscalDateEnding', 'price_date_start', 'price_start', 'price_end',
            'pe_ratio', 'earnings_yield', 'return_on_capital', 'debt_ratio', 'debt_to_equity', 
            'current_ratio', 'profit_margin', 'asset_turnover', 'book_to_market', 
            'rev_growth', 'ebit_growth', 'target_return'
        ]
        
        return df_funds[final_columns].dropna()
    except Exception as e:
        print(f"Error processing {overview_json.get('Symbol')}: {e}")
        return None

# --- MAIN EXECUTION LOOP (Unchanged) ---
master_list = []

for symbol in TICKERS:
    print(f"Fetching data for: {symbol}...")
    try:
        endpoints = {'income': 'INCOME_STATEMENT', 'balance': 'BALANCE_SHEET', 
                     'overview': 'OVERVIEW', 'price': 'TIME_SERIES_MONTHLY_ADJUSTED'}
        data_bundle = {}
        for key, func in endpoints.items():
            res = requests.get(BASE_URL, params={'function': func, 'symbol': symbol, 'apikey': API_KEY})
            json_data = res.json()
            if "Note" in json_data:
                print("Rate limit. Waiting...")
                time.sleep(60)
                json_data = requests.get(BASE_URL, params={'function': func, 'symbol': symbol, 'apikey': API_KEY}).json()
            data_bundle[key] = json_data
            time.sleep(15)

        ticker_df = prepare_point_in_time_dataset(data_bundle['income'], data_bundle['balance'], 
                                                 data_bundle['overview'], data_bundle['price'])
        if ticker_df is not None:
            master_list.append(ticker_df)
    except Exception as e:
        print(f"Error: {e}")

if master_list:
    pd.concat(master_list).to_csv(OUTPUT_FILE, index=False)
    print("Done!")