"""
File-based cooldown persistence so repeated GitHub Actions runs don't
spam duplicate alerts for the same symbol+direction within COOLDOWN_HOURS.
"""

import json
import os
from datetime import datetime, timedelta, timezone

WAT = timezone(timedelta(hours=1))


def load_sent_signals(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_sent_signals(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def is_on_cooldown(data: dict, key: str, cooldown_hours: int) -> bool:
    if key not in data:
        return False
    last_sent = datetime.fromisoformat(data[key])
    return datetime.now(WAT) - last_sent < timedelta(hours=cooldown_hours)


def mark_sent(data: dict, key: str) -> dict:
    data[key] = datetime.now(WAT).isoformat()
    return data
  
