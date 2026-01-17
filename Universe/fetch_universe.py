import yaml
import os
import json
from datetime import datetime

# Load config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")

with open(CONFIG_PATH) as f:
    config = yaml.safe_load(f)

RAW_PATH = config['raw_prices_path']
LOG_FILE = config['log_file']

# Example: manually define S&P 500 tickers to start
# Later, you can replace this with a dynamic API fetch if available
sp500_tickers = ["AAPL","GOOG"]  # start small

# Save universe to file
universe_file = os.path.join(RAW_PATH, "universe.json")
os.makedirs(RAW_PATH, exist_ok=True)

with open(universe_file, "w") as f:
    json.dump(sp500_tickers, f, indent=2)

# Logging
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
with open(LOG_FILE, "a") as log:
    log.write(f"{datetime.now()} - Universe saved with {len(sp500_tickers)} tickers\n")

print(f"Universe saved to {universe_file}")
