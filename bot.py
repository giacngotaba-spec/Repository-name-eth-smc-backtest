import os
import time
from pathlib import Path

import pandas as pd
import requests

DATA_DIR = Path("user_data/data/binance")
DATA_FILE = DATA_DIR / "ETH_USDT-5m.feather"
BINANCE_URL = "https://api.binance.com/api/v3/klines"


def fetch_eth_5m_data(limit: int = 1000):
    """Fetch recent ETH/USDT 5m candles from Binance."""
    params = {
        "symbol": "ETHUSDT",
        "interval": "5m",
        "limit": limit,
    }
    headers = {"User-Agent": "Mozilla/5.0"}

    for attempt in range(3):
        try:
            response = requests.get(BINANCE_URL, params=params, headers=headers, timeout=20)
            print(f"Binance status: {response.status_code}")

            if response.status_code == 451:
                print("❌ Binance blocked this IP/region (HTTP 451).")
                return None

            response.raise_for_status()
            raw = response.json()
            if not raw:
                print("⚠️ Empty Binance response.")
                return None

            cols = [
                "open_time",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "close_time",
                "quote_asset_volume",
                "number_of_trades",
                "taker_buy_base_asset_volume",
                "taker_buy_quote_asset_volume",
                "ignore",
            ]
            df = pd.DataFrame(raw, columns=cols)
            df["date"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)

            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            df = df[["date", "open", "high", "low", "close", "volume"]].dropna().reset_index(drop=True)
            return df

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
    print("🤖 Starting ETH bot...")

    df = fetch_eth_5m_data(limit=1000)
    if df is not None:
        save_data(df)
        send_telegram_message(f"<b>ETH/USDT</b> dataset refreshed successfully. Rows: {len(df)}")
    else:
        if DATA_FILE.exists():
            print(f"⚠️ Using existing file: {DATA_FILE}")
        else:
            save_data(None)
            send_telegram_message("<b>ETH/USDT</b> bot started but no market data was available from Binance.")

    print("✅ Bot run complete")


if __name__ == "__main__":
    main()
