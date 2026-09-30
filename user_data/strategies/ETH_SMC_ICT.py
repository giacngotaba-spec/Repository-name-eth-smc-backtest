from freqtrade.strategy import IStrategy
from pandas import DataFrame
import numpy as np


class ETH_SMC_ICT(IStrategy):

    INTERFACE_VERSION = 3

    timeframe = "5m"
    can_short = True

    startup_candle_count = 250

    minimal_roi = {
        "0": 0.03,
        "60": 0.02,
        "180": 0.01,
        "360": 0
    }

    stoploss = -0.025

    trailing_stop = False

    process_only_new_candles = True

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = True

    def populate_indicators(
        self,
        dataframe: DataFrame,
        metadata: dict
    ) -> DataFrame:

        df = dataframe

        # EMA
        df["ema20"] = df["close"].ewm(
            span=20,
            adjust=False
        ).mean()

        df["ema50"] = df["close"].ewm(
            span=50,
            adjust=False
        ).mean()

        df["ema200"] = df["close"].ewm(
            span=200,
            adjust=False
        ).mean()

        # Volume
        df["volume_ma20"] = (
            df["volume"].rolling(20).mean()
        )

        df["volume_ratio"] = (
            df["volume"] /
            df["volume_ma20"].replace(0, np.nan)
        )

        # ATR
        high_low = df["high"] - df["low"]

        high_close = (
            df["high"] -
            df["close"].shift()
        ).abs()

        low_close = (
            df["low"] -
            df["close"].shift()
        ).abs()

        tr = np.maximum(
            high_low,
            np.maximum(high_close, low_close)
        )

        df["atr"] = (
            tr.rolling(14).mean()
        )

        # Swing high / low
        df["swing_high"] = (
            df["high"]
            .shift(1)
            .rolling(5)
            .max()
        )

        df["swing_low"] = (
            df["low"]
            .shift(1)
            .rolling(5)
            .min()
        )

        # BOS
        df["bos_up"] = (
            df["close"] >
            df["swing_high"]
        )

        df["bos_down"] = (
            df["close"] <
            df["swing_low"]
        )

        # Liquidity sweep
        previous_low = (
            df["low"]
            .shift(1)
            .rolling(10)
            .min()
        )

        previous_high = (
            df["high"]
            .shift(1)
            .rolling(10)
            .max()
        )

        df["sweep_low"] = (
            (df["low"] < previous_low) &
            (df["close"] > previous_low)
        )

        df["sweep_high"] = (
            (df["high"] > previous_high) &
            (df["close"] < previous_high)
        )

        # ICT Fair Value Gap
        df["bullish_fvg"] = (
            df["low"] >
            df["high"].shift(2)
        )

        df["bearish_fvg"] = (
            df["high"] <
            df["low"].shift(2)
        )

        # Candle body
        candle_range = (
            df["high"] - df["low"]
        ).replace(0, np.nan)

        df["body_ratio"] = (
            (df["close"] - df["open"]).abs()
            / candle_range
        )

        df["bullish_candle"] = (
            (df["close"] > df["open"]) &
            (df["body_ratio"] > 0.45)
        )

        df["bearish_candle"] = (
            (df["close"] < df["open"]) &
            (df["body_ratio"] > 0.45)
        )

        # Trend
        df["trend_up"] = (
            (df["ema50"] > df["ema200"]) &
            (df["close"] > df["ema50"])
        )

        df["trend_down"] = (
            (df["ema50"] < df["ema200"]) &
            (df["close"] < df["ema50"])
        )

        return df

    def populate_entry_trend(
        self,
        dataframe: DataFrame,
        metadata: dict
    ) -> DataFrame:

        df = dataframe

        # LONG
        long_condition = (
            df["trend_up"] &
            (
                df["sweep_low"] |
                df["bullish_fvg"]
            ) &
            df["bos_up"] &
            df["bullish_candle"] &
            (df["volume_ratio"] > 1.0) &
            (df["volume"] > 0)
        )

        df.loc[
            long_condition,
            "enter_long"
        ] = 1

        df.loc[
            long_condition,
            "enter_tag"
        ] = "SMC_ICT_LONG"

        # SHORT
        short_condition = (
            df["trend_down"] &
            (
                df["sweep_high"] |
                df["bearish_fvg"]
            ) &
            df["bos_down"] &
            df["bearish_candle"] &
            (df["volume_ratio"] > 1.0) &
            (df["volume"] > 0)
        )

        df.loc[
            short_condition,
            "enter_short"
        ] = 1

        df.loc[
            short_condition,
            "enter_tag"
        ] = "SMC_ICT_SHORT"

        return df

    def populate_exit_trend(
        self,
        dataframe: DataFrame,
        metadata: dict
    ) -> DataFrame:

        df = dataframe

        # Thoát LONG
        exit_long = (
            (df["close"] < df["ema20"]) &
            df["bearish_candle"]
        )

        df.loc[
            exit_long,
            "exit_long"
        ] = 1

        df.loc[
            exit_long,
            "exit_tag"
        ] = "EXIT_LONG"

        # Thoát SHORT
        exit_short = (
            (df["close"] > df["ema20"]) &
            df["bullish_candle"]
        )

        df.loc[
            exit_short,
            "exit_short"
        ] = 1

        df.loc[
            exit_short,
            "exit_tag"
        ] = "EXIT_SHORT"

        return df