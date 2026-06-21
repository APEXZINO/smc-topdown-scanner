"""
Zone detection: Order Blocks (OB), Fair Value Gaps (FVG),
Supply/Demand zones, and 15-min reversal/confirmation candles.
"""

import pandas as pd


def find_order_blocks(df: pd.DataFrame, bias: str, lookback: int = 20) -> list:
    """
    A bullish Order Block = last down-close candle before a strong up-move.
    A bearish Order Block = last up-close candle before a strong down-move.
    Returns a list of zones (each a dict with top/bottom/time).
    """
    recent = df.tail(lookback).reset_index(drop=True)
    obs = []

    for i in range(1, len(recent) - 1):
        candle = recent.iloc[i]
        next_candle = recent.iloc[i + 1]
        body = abs(next_candle["close"] - next_candle["open"])
        avg_range = (recent["high"] - recent["low"]).mean()

        is_impulsive = body > avg_range * 1.3

        if bias == "bullish":
            is_down_candle = candle["close"] < candle["open"]
            moves_up = next_candle["close"] > candle["high"]
            if is_down_candle and is_impulsive and moves_up:
                obs.append({"top": float(candle["high"]), "bottom": float(candle["low"]),
                            "time": str(candle["time"])})

        elif bias == "bearish":
            is_up_candle = candle["close"] > candle["open"]
            moves_down = next_candle["close"] < candle["low"]
            if is_up_candle and is_impulsive and moves_down:
                obs.append({"top": float(candle["high"]), "bottom": float(candle["low"]),
                            "time": str(candle["time"])})

    return obs[-3:]  # most recent 3 zones


def find_fair_value_gaps(df: pd.DataFrame, bias: str, lookback: int = 20) -> list:
    """
    3-candle imbalance pattern:
    Bullish FVG: candle1.high < candle3.low (gap left behind in an up-move)
    Bearish FVG: candle1.low  > candle3.high (gap left behind in a down-move)
    """
    recent = df.tail(lookback).reset_index(drop=True)
    fvgs = []

    for i in range(len(recent) - 2):
        c1, c3 = recent.iloc[i], recent.iloc[i + 2]

        if bias == "bullish" and c1["high"] < c3["low"]:
            fvgs.append({"top": float(c3["low"]), "bottom": float(c1["high"]),
                         "time": str(recent.iloc[i + 1]["time"])})

        elif bias == "bearish" and c1["low"] > c3["high"]:
            fvgs.append({"top": float(c1["low"]), "bottom": float(c3["high"]),
                         "time": str(recent.iloc[i + 1]["time"])})

    return fvgs[-3:]


def find_supply_demand_zone(df: pd.DataFrame, bias: str, lookback: int = 30) -> dict:
    """
    Identifies a base (tight consolidation) immediately preceding a strong
    directional move -- the origin of a supply or demand zone.
    """
    recent = df.tail(lookback).reset_index(drop=True)
    avg_range = (recent["high"] - recent["low"]).mean()

    for i in range(2, len(recent) - 1):
        base = recent.iloc[i - 2:i]
        breakout = recent.iloc[i]
        base_tight = (base["high"].max() - base["low"].min()) < avg_range * 1.2
        strong_move = abs(breakout["close"] - breakout["open"]) > avg_range * 1.5

        if base_tight and strong_move:
            moved_up = breakout["close"] > breakout["open"]
            if bias == "bullish" and moved_up:
                return {"type": "demand", "top": float(base["high"].max()),
                        "bottom": float(base["low"].min())}
            if bias == "bearish" and not moved_up:
                return {"type": "supply", "top": float(base["high"].max()),
                        "bottom": float(base["low"].min())}

    return {}


def price_in_zone(price: float, zone: dict, tolerance_pct: float = 0.15) -> bool:
    """Checks if price is inside (or just touching) a top/bottom zone."""
    if not zone or "top" not in zone:
        return False
    span = zone["top"] - zone["bottom"]
    buffer = span * tolerance_pct
    return (zone["bottom"] - buffer) <= price <= (zone["top"] + buffer)


def detect_reversal_confirmation(df: pd.DataFrame, bias: str) -> dict:
    """
    Looks for a confirmation candle on the LTF (15min): bullish/bearish
    engulfing, or a pin bar / rejection wick, in the direction of `bias`.
    """
    if len(df) < 2:
        return {"confirmed": False, "pattern": None}

    prev, last = df.iloc[-2], df.iloc[-1]
    body = abs(last["close"] - last["open"])
    full_range = last["high"] - last["low"] if last["high"] != last["low"] else 1e-9
    upper_wick = last["high"] - max(last["close"], last["open"])
    lower_wick = min(last["close"], last["open"]) - last["low"]

    if bias == "bullish":
        engulfing = (last["close"] > last["open"] and prev["close"] < prev["open"]
                     and last["close"] > prev["open"] and last["open"] < prev["close"])
        pin_bar = lower_wick > body * 2 and lower_wick / full_range > 0.5
        if engulfing:
            return {"confirmed": True, "pattern": "bullish_engulfing"}
        if pin_bar:
            return {"confirmed": True, "pattern": "bullish_pin_bar"}

    elif bias == "bearish":
        engulfing = (last["close"] < last["open"] and prev["close"] > prev["open"]
                     and last["close"] < prev["open"] and last["open"] > prev["close"])
        pin_bar = upper_wick > body * 2 and upper_wick / full_range > 0.5
        if engulfing:
            return {"confirmed": True, "pattern": "bearish_engulfing"}
        if pin_bar:
            return {"confirmed": True, "pattern": "bearish_pin_bar"}

    return {"confirmed": False, "pattern": None}
