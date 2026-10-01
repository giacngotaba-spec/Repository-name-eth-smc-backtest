import json
from pathlib import Path

import pandas as pd

from strategy import add_indicators

DATA_PATH = Path("user_data/data/binance/ETH_USDT-5m.feather")
REPORT_PATH = Path("reports/backtest_summary.json")


def load_data(path: Path = DATA_PATH) -> pd.DataFrame:
    if not path.exists():
        print(f"⚠️ Data file not found: {path}")
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

    df = pd.read_feather(path)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], utc=True)
    return df.sort_values("date").reset_index(drop=True)


def run_backtest(df: pd.DataFrame):
    if df.empty:
        summary = {
            "status": "no_data",
            "message": "No ETH dataset available.",
            "signal": 0,
            "rows": 0,
            "total_return": 0.0,
            "win_rate": 0.0,
        }
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return summary

    data = add_indicators(df)
    data["returns"] = data["close"].pct_change().fillna(0.0)
    data["strategy_return"] = data["returns"] * data["signal"].shift(1).fillna(0.0)
    data["equity"] = (1 + data["strategy_return"]).cumprod()

    total_return = float(data["equity"].iloc[-1] - 1.0) if not data.empty else 0.0
    wins = (data["strategy_return"] > 0).sum()
    losses = (data["strategy_return"] <= 0).sum()
    win_rate = (wins / (wins + losses)) if (wins + losses) > 0 else 0.0

    summary = {
        "status": "ok",
        "rows": int(len(data)),
        "signal": int(data["signal"].iloc[-1]),
        "total_return": round(total_return, 6),
        "win_rate": round(win_rate, 4),
        "first_date": data["date"].iloc[0].isoformat() if not data.empty else None,
        "last_date": data["date"].iloc[-1].isoformat() if not data.empty else None,
        "final_equity": round(float(data["equity"].iloc[-1]), 6) if not data.empty else 0.0,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    df = load_data()
    run_backtest(df)
