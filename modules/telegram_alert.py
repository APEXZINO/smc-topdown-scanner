"""
Telegram alert sender. Sends a formatted top-down confluence breakdown.
"""

import requests


def send_telegram_alert(token: str, chat_id: str, symbol: str, bias: str,
                         result: dict, price: float, wat_time: str) -> bool:
    direction_emoji = "🟢" if bias == "bullish" else "🔴"
    checklist_lines = []
    for item in result["checklist"]:
        mark = "✅" if item["met"] else "❌"
        checklist_lines.append(f"{mark} {item['criterion']}")

    message = (
        f"{direction_emoji} <b>{symbol} — {bias.upper()} SETUP</b>\n"
        f"🕐 {wat_time} WAT\n"
        f"💰 Price: {price}\n"
        f"📊 Confluence: {result['score']}/{result['max_score']} "
        f"({result['percentage']}%) — {result['signal_grade']}\n\n"
        f"<b>Top-down checklist:</b>\n" + "\n".join(checklist_lines)
    )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}

    try:
        resp = requests.post(url, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"Telegram send failed: {e}")
        return False
      
