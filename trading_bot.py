import json
from pathlib import Path

from flask import Flask, jsonify

from strategy import generate_signal_summary

REPORT_PATH = Path("reports/backtest_summary.json")
DATA_PATH = Path("user_data/data/binance/ETH_USDT-5m.feather")

app = Flask(__name__)


def load_summary():
    if REPORT_PATH.exists():
        try:
            return json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"status": "no_report"}


@app.route("/")
def index():
    summary = load_summary()
    return jsonify({"service": "ETH strategy dashboard", "summary": summary})


@app.route("/api/summary")
def api_summary():
    summary = load_summary()
    return jsonify(summary)


@app.route("/api/signal")
def api_signal():
    if not DATA_PATH.exists():
        return jsonify({"status": "no_data", "signal": 0})

    import pandas as pd
    df = pd.read_feather(DATA_PATH)
    return jsonify(generate_signal_summary(df))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
