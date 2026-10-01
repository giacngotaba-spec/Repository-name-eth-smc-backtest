import pandas as pd


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if df.empty:
        return df

    df["ema_short"] = df["close"].ewm(span=9, adjust=False).mean()
    df["ema_long"] = df["close"].ewm(span=21, adjust=False).mean()
    df["signal"] = (df["ema_short"] > df["ema_long"]).astype(int)
    df["position"] = df["signal"].diff().fillna(0)
    return df


def generate_signal_summary(df: pd.DataFrame):
    if df.empty:
        return {"status": "no_data", "signal": 0, "position": 0}

    signal_df = add_indicators(df)
    last_signal = int(signal_df["signal"].iloc[-1])
    last_position = int(signal_df["position"].iloc[-1])
    return {
        "status": "ok",
        "signal": last_signal,
        "position": last_position,
        "ema_short": float(signal_df["ema_short"].iloc[-1]),
        "ema_long": float(signal_df["ema_long"].iloc[-1]),
        "close": float(signal_df["close"].iloc[-1]),
    }
