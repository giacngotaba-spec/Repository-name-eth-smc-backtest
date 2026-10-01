import os
import time
from pathlib import Path

import pandas as pd
import requests

DATA_DIR = Path("user_data/data/binance")
DATA_FILE = DATA_DIR / "ETH_USDT-5m.feather"
KUCOIN_URL = "https://api.kucoin.com/api/v1/market/candles"


def fetch_eth_5m_data(limit: int = 1000):
    """Fetch recent ETH/USDT 5m candles from KuCoin."""
    params = {
        "type": "5min",
        "symbol": "ETH-USDT",
        "limit": limit,
    }
    headers = {"User-Agent": "Mozilla/5.0"}

    for attempt in range(3):
        try:
            response = requests.get(KUCOIN_URL, params=params, headers=headers, timeout=20)
            print(f"KuCoin status: {response.status_code}")
            response.raise_for_status()
            payload = response.json()

            if payload.get("code") != "200000":
                print(f"⚠️ KuCoin error payload: {payload}")
                return None

            raw = payload.get("data", [])
            if not raw:
                print("⚠️ Empty KuCoin response.")
                return None

            rows = []
            for item in raw:
                # KuCoin candles format: [time, open, close, high, low, volume, turnover]
                candle_time = pd.to_datetime(item[0], unit="ms", utc=True)
                rows.append({
                    "date": candle_time,
                    "open": float(item[1]),
                    "high": float(item[3]),
                    "low": float(item[4]),
                    "close": float(item[2]),
                    "volume": float(item[5]),
                })

            df = pd.DataFrame(rows)
            if df.empty:
                return None
            return df[["date", "open", "high", "low", "close", "volume"]].dropna().reset_index(drop=True)

        except Exception as exc:
            print(f"⚠️ Attempt {attempt + 1} failed: {exc}")
            time.sleep(2)

    return None


def save_data(df):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if df is None or df.empty:
        print("⚠️ No data available. Creating empty placeholder.")
        df = pd.DataFrame({
            "date": pd.to_datetime([], utc=True),
            "open": [],
            "high": [],
            "low": [],
            "close": [],
            "volume": [],
        })

    df = df.sort_values("date").drop_duplicates(subset=["date"]).reset_index(drop=True)
    df.to_feather(DATA_FILE)
    print(f"✅ Saved ETH/USDT 5m data to {DATA_FILE}")


def send_telegram_message(message: str):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("⚠️ Telegram not configured; skipping notification.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    try:
        response = requests.post(url, data=payload, timeout=20)
        response.raise_for_status()
        print("✅ Telegram notification sent.")
    except Exception as exc:
        print(f"⚠️ Telegram send failed: {exc}")


def main():
    print("🤖 Starting ETH bot with KuCoin...")

    df = fetch_eth_5m_data(limit=1000)
    if df is not None:
        save_data(df)
        send_telegram_message(f"<b>ETH/USDT</b> dataset refreshed successfully from KuCoin. Rows: {len(df)}")
    else:
        if DATA_FILE.exists():
            print(f"⚠️ Using existing file: {DATA_FILE}")
        else:
            save_data(None)
            send_telegram_message("<b>ETH/USDT</b> bot started but no market data was available from KuCoin.")

    print("✅ Bot run complete")


if __name__ == "__main__":
    main()
