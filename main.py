"""
SMC/ICT Top-Down Scanner
4H (Direction, Key Levels, Supply/Demand)
  -> 1H (BOS/CHoCH, Order Block, FVG)
    -> 15min (Liquidity Sweep, Reversal Confirmation)

Runs as a single pass, intended to be triggered on a schedule by
GitHub Actions (see .github/workflows/scanner.yml).
"""

import os
import sys
from datetime import datetime, timezone, timedelta

from modules.deriv_api import fetch_candles
from modules.structure import determine_trend, get_key_levels, detect_bos_choch, detect_liquidity_sweep
from modules.zones import (
    find_order_blocks, find_fair_value_gaps, find_supply_demand_zone,
    price_in_zone, detect_reversal_confirmation,
)
from modules.confluence import score_confluence
from modules.telegram_alert import send_telegram_alert
from modules.persistence import load_sent_signals, save_sent_signals, is_on_cooldown, mark_sent

# ---------------- CONFIG ----------------
SYMBOLS = ["R_75", "R_100", "R_50", "R_25"]  # edit to your preferred synthetic indices
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "388117501")
DATA_FILE = "data/sent_signals.json"
COOLDOWN_HOURS = 4

WAT = timezone(timedelta(hours=1))


def analyze_symbol(symbol: str) -> dict | None:
    """Runs the full 4H -> 1H -> 15min pipeline for one symbol."""

    df_4h = fetch_candles(symbol, "4H", count=120)
    df_1h = fetch_candles(symbol, "1H", count=150)
    df_15m = fetch_candles(symbol, "15M", count=150)

    # ---- 4H: Direction, Key Levels, Supply/Demand ----
    bias = determine_trend(df_4h)
    if bias == "ranging":
        return None  # no clear HTF direction, skip symbol this run

    key_levels = get_key_levels(df_4h)
    sd_zone = find_supply_demand_zone(df_4h, bias)
    current_price = df_15m["close"].iloc[-1]

    near_key_level = any(
        abs(current_price - lvl) / current_price < 0.01
        for lvl in key_levels["resistance_levels"] + key_levels["support_levels"]
    )
    in_sd_zone = price_in_zone(current_price, sd_zone)

    # ---- 1H: Breaks, Order Block, FVG ----
    break_info = detect_bos_choch(df_1h, bias)
    obs = find_order_blocks(df_1h, bias)
    fvgs = find_fair_value_gaps(df_1h, bias)

    in_ob = any(price_in_zone(current_price, ob) for ob in obs)
    in_fvg = any(price_in_zone(current_price, fvg) for fvg in fvgs)

    # ---- 15min: Liquidity Sweep, Reversal Confirmation ----
    sweep = detect_liquidity_sweep(df_15m, bias)
    confirmation = detect_reversal_confirmation(df_15m, bias)

    criteria = {
        "htf_direction": True,  # already filtered out 'ranging' above
        "htf_key_level": near_key_level,
        "htf_supply_demand": in_sd_zone,
        "mtf_break": break_info["break_detected"],
        "mtf_order_block": in_ob,
        "mtf_fvg": in_fvg,
        "ltf_liquidity_sweep": sweep["swept"],
        "ltf_confirmation": confirmation["confirmed"],
    }

    result = score_confluence(criteria)
    result["bias"] = bias
    result["price"] = float(current_price)
    result["symbol"] = symbol

    return result


def main():
    if not TELEGRAM_TOKEN:
        print("WARNING: TELEGRAM_TOKEN not set. Alerts will not be sent.")

    sent_data = load_sent_signals(DATA_FILE)
    now_wat = datetime.now(WAT).strftime("%Y-%m-%d %H:%M")

    for symbol in SYMBOLS:
        try:
            result = analyze_symbol(symbol)
        except Exception as e:
            print(f"[{symbol}] ERROR: {e}")
            continue

        if result is None:
            print(f"[{symbol}] No clear 4H bias — skipped.")
            continue

        print(f"[{symbol}] bias={result['bias']} score={result['score']}/{result['max_score']} "
              f"grade={result['signal_grade']}")

        if not result["tradeable"]:
            continue

        cooldown_key = f"{symbol}_{result['bias']}"
        if is_on_cooldown(sent_data, cooldown_key, COOLDOWN_HOURS):
            print(f"[{symbol}] Signal on cooldown — skipping alert.")
            continue

        if TELEGRAM_TOKEN:
            sent_ok = send_telegram_alert(
                TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, symbol, result["bias"],
                result, result["price"], now_wat,
            )
            if sent_ok:
                sent_data = mark_sent(sent_data, cooldown_key)
                print(f"[{symbol}] Alert sent.")
            else:
                print(f"[{symbol}] Alert failed to send.")

    save_sent_signals(DATA_FILE, sent_data)


if __name__ == "__main__":
    sys.exit(main())
  
