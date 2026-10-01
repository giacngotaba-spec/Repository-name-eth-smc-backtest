import json
import os
from pathlib import Path

import pandas as pd
import requests

from strategy import generate_signal_summary

DATA_PATH = Path("user_data/data/binance/ETH_USDT-5m.feather")
REPORT_PATH = Path("reports/paper_trade.json")


def load_data(path: Path = DATA_PATH) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
    df = pd.read_feather(path)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], utc=True)
    return df.sort_values("date").reset_index(drop=True)


def send_telegram(message: str):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("⚠️ Telegram not configured. Skipping signal message.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    try:
        response = requests.post(url, data=payload, timeout=20)
        response.raise_for_status()
        print("✅ Telegram signal sent.")
    except Exception as exc:
        print(f"⚠️ Signal message failed: {exc}")


def run_paper_trade():
    df = load_data()
    if df.empty:
        result = {"status": "no_data", "action": "hold"}
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
        return result

    summary = generate_signal_summary(df)
    action = "buy" if summary["signal"] == 1 else "sell" if summary["signal"] == 0 else "hold"

    result = {
        "status": "ok",
        "action": action,
        "signal": summary["signal"],
        "close": round(summary["close"], 4),
        "ema_short": round(summary["ema_short"], 4),
        "ema_long": round(summary["ema_long"], 4),
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")

    if action == "buy":
        msg = f"<b>ETH/USDT</b> BUY signal: price {result['close']} | EMA9 {result['ema_short']} > EMA21 {result['ema_long']}"
    elif action == "sell":
        msg = f"<b>ETH/USDT</b> SELL signal: price {result['close']} | EMA9 {result['ema_short']} <= EMA21 {result['ema_long']}"
    else:
        msg = f"<b>ETH/USDT</b> HOLD signal: price {result['close']}"

    send_telegram(msg)
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    run_paper_trade()
