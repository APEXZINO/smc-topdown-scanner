"""
Confluence scoring engine.

Weights reflect which criteria from the 4H -> 1H -> 15min framework
are the strongest standalone predictors vs. which are supporting context only.
Liquidity sweep + BOS/CHoCH + OB/FVG retest + LTF confirmation (the classic
ICT entry model) carries the most weight; HTF context (direction, key levels,
supply/demand) sets up the trade but isn't an entry trigger on its own.
"""

# criterion: (weight, description)
WEIGHTS = {
    "htf_direction": (1, "4H directional bias established"),
    "htf_key_level": (1, "Price reacting near a 4H key level"),
    "htf_supply_demand": (1, "4H supply/demand zone aligned with bias"),
    "mtf_break": (2, "1H BOS/CHoCH confirms HTF bias"),
    "mtf_order_block": (2, "1H Order Block present in bias direction"),
    "mtf_fvg": (1, "1H Fair Value Gap present in bias direction"),
    "ltf_liquidity_sweep": (2, "15min liquidity sweep (stop hunt) into zone"),
    "ltf_confirmation": (2, "15min reversal/confirmation candle"),
}

MAX_SCORE = sum(w for w, _ in WEIGHTS.values())  # 12
SIGNAL_THRESHOLD = 8  # require strong confluence before alerting


def score_confluence(criteria: dict) -> dict:
    """
    `criteria` is a dict of {criterion_name: bool}.
    Returns total score, max score, percentage, and a checklist for the alert.
    """
    total = 0
    checklist = []

    for name, (weight, desc) in WEIGHTS.items():
        met = bool(criteria.get(name, False))
        if met:
            total += weight
        checklist.append({"criterion": desc, "met": met, "weight": weight})

    return {
        "score": total,
        "max_score": MAX_SCORE,
        "percentage": round((total / MAX_SCORE) * 100, 1),
        "checklist": checklist,
        "signal_grade": grade(total),
        "tradeable": total >= SIGNAL_THRESHOLD,
    }


def grade(score: int) -> str:
    if score >= 10:
        return "A (high confluence)"
    if score >= 8:
        return "B (tradeable confluence)"
    if score >= 5:
        return "C (weak / watch only)"
    return "D (no setup)"
  
