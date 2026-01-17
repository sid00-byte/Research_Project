import requests
import time
import os
import json
import yaml
from datetime import datetime

# ----------------------------
# Load config
# ----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")

with open(CONFIG_PATH) as f:
    config = yaml.safe_load(f)

API_KEY = config["api_key"]
RAW_PATH = os.path.join(BASE_DIR, config.get("raw_prices_path", "raw/prices"))
LOG_FILE = os.path.join(BASE_DIR, config.get("log_file", "logs/fetch_log.txt"))
RETRY = config.get("retry_attempts", 3)
SLEEP = config.get("sleep_seconds", 15)

# ----------------------------
# Load universe
# ----------------------------
UNIVERSE_FILE = os.path.join(BASE_DIR, "raw/prices/universe.json")

with open(UNIVERSE_FILE) as f:
    tickers = json.load(f)

os.makedirs(RAW_PATH, exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

ALPHA_URL = "https://www.alphavantage.co/query"
MONTHLY_KEY = "Monthly Adjusted Time Series"

# ----------------------------
# Fetch function
# ----------------------------
def fetch_price(ticker):
    params = {
        "function": "TIME_SERIES_MONTHLY_ADJUSTED",
        "symbol": ticker,
        "apikey": API_KEY
    }

    for attempt in range(1, RETRY + 1):
        try:
            full_url = requests.Request("GET", ALPHA_URL, params=params).prepare().url
            print(f"[DEBUG] Requesting URL: {full_url}")

            response = requests.get(ALPHA_URL, params=params, timeout=30)

            if response.status_code == 503:
                print(f"[{ticker}] HTTP 503 – sleeping 60s")
                time.sleep(60)
                continue

            response.raise_for_status()
            data = response.json()

            print(f"[{ticker}] Response keys: {list(data.keys())}")

            # API rate limit
            if "Note" in data:
                print(f"[{ticker}] API limit hit – sleeping 60s")
                time.sleep(60)
                continue

            # ✅ CORRECT KEY CHECK
            if MONTHLY_KEY in data:
                return data

            raise ValueError("Monthly data key missing")

        except Exception as e:
            print(f"[{ticker}] Attempt {attempt} failed: {e}")
            with open(LOG_FILE, "a") as log:
                log.write(f"{datetime.now()} - Attempt {attempt} failed for {ticker}: {e}\n")
            time.sleep(SLEEP)

    return None

# ----------------------------
# Main loop
# ----------------------------
for ticker in tickers:
    print(f"\nFetching {ticker}...")
    data = fetch_price(ticker)

    if data:
        out_file = os.path.join(
            RAW_PATH, f"{ticker}_monthly_adjusted.json"
        )
        with open(out_file, "w") as f:
            json.dump(data, f, indent=2)

        print(f"[{ticker}] Saved successfully")
        with open(LOG_FILE, "a") as log:
            log.write(f"{datetime.now()} - Successfully fetched {ticker}\n")
    else:
        print(f"[{ticker}] Failed after {RETRY} attempts")
        with open(LOG_FILE, "a") as log:
            log.write(f"{datetime.now()} - Failed to fetch {ticker}\n")

    time.sleep(SLEEP)
