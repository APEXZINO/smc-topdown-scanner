"""
Market structure detection: swing highs/lows, trend direction,
Break of Structure (BOS), Change of Character (CHoCH), and
liquidity pools (equal highs/lows + sweeps).
"""

import pandas as pd


def find_swing_points(df: pd.DataFrame, window: int = 3) -> pd.DataFrame:
    """
    Marks swing highs and swing lows using a simple fractal: a candle's
    high/low must be the highest/lowest within `window` candles on each side.
    Adds boolean columns 'swing_high' and 'swing_low'.
    """
    df = df.copy()
    df["swing_high"] = False
    df["swing_low"] = False

    for i in range(window, len(df) - window):
        local_high = df["high"].iloc[i - window: i + window + 1]
        local_low = df["low"].iloc[i - window: i + window + 1]

        if df["high"].iloc[i] == local_high.max():
            df.loc[df.index[i], "swing_high"] = True
        if df["low"].iloc[i] == local_low.min():
            df.loc[df.index[i], "swing_low"] = True

    return df


def get_key_levels(df: pd.DataFrame, n: int = 4) -> dict:
    """
    Returns the most recent `n` swing highs and lows as key levels.
    """
    swings = find_swing_points(df)
    highs = swings[swings["swing_high"]].tail(n)["high"].tolist()
    lows = swings[swings["swing_low"]].tail(n)["low"].tolist()
    return {"resistance_levels": highs, "support_levels": lows}


def determine_trend(df: pd.DataFrame) -> str:
    """
    Determines HTF directional bias from the sequence of recent swing points.
    Returns 'bullish', 'bearish', or 'ranging'.
    """
    swings = find_swing_points(df)
    highs = swings[swings["swing_high"]].tail(3)["high"].tolist()
    lows = swings[swings["swing_low"]].tail(3)["low"].tolist()

    if len(highs) >= 2 and len(lows) >= 2:
        higher_highs = highs[-1] > highs[-2]
        higher_lows = lows[-1] > lows[-2]
        lower_highs = highs[-1] < highs[-2]
        lower_lows = lows[-1] < lows[-2]

        if higher_highs and higher_lows:
            return "bullish"
        if lower_highs and lower_lows:
            return "bearish"

    return "ranging"


def detect_bos_choch(df: pd.DataFrame, bias: str) -> dict:
    """
    Detects whether the most recent close has broken the last relevant
    swing level in the direction of `bias` (BOS = continuation,
    CHoCH = first break against the prior structure).
    """
    swings = find_swing_points(df)
    last_close = df["close"].iloc[-1]

    recent_highs = swings[swings["swing_high"]].tail(2)["high"].tolist()
    recent_lows = swings[swings["swing_low"]].tail(2)["low"].tolist()

    result = {"break_detected": False, "break_type": None, "level": None}

    if bias == "bullish" and recent_highs:
        level = recent_highs[-1]
        if last_close > level:
            result = {"break_detected": True, "break_type": "BOS", "level": level}

    elif bias == "bearish" and recent_lows:
        level = recent_lows[-1]
        if last_close < level:
            result = {"break_detected": True, "break_type": "BOS", "level": level}

    # CHoCH: price breaks structure opposite to prior trend
    prior_trend = determine_trend(df.iloc[:-5]) if len(df) > 10 else "ranging"
    if result["break_detected"] and prior_trend != "ranging" and prior_trend != bias:
        result["break_type"] = "CHoCH"

    return result


def detect_liquidity_sweep(df: pd.DataFrame, bias: str, lookback: int = 10) -> dict:
    """
    Detects a liquidity sweep: price wicks beyond a recent swing high/low
    then closes back inside range (a stop-hunt / inducement before reversal).
    """
    recent = df.tail(lookback)
    last = df.iloc[-1]

    if bias == "bullish":
        prior_low = recent["low"].iloc[:-1].min()
        swept = last["low"] < prior_low and last["close"] > prior_low
        return {"swept": bool(swept), "level": float(prior_low)}

    if bias == "bearish":
        prior_high = recent["high"].iloc[:-1].max()
        swept = last["high"] > prior_high and last["close"] < prior_high
        return {"swept": bool(swept), "level": float(prior_high)}

    return {"swept": False, "level": None}
      
