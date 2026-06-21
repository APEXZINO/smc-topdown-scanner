"""
Deriv WebSocket API helper.
Fetches historical candles for a given symbol/granularity.
No authentication required for market data (app_id=1089).
"""

import json
import time
import websocket
import pandas as pd

APP_ID = "1089"
WS_URL = f"wss://ws.derivws.com/websockets/v3?app_id={APP_ID}"

# Granularity in seconds
GRANULARITY = {
    "4H": 14400,
    "1H": 3600,
    "15M": 900,
}


def fetch_candles(symbol: str, timeframe: str, count: int = 150, retries: int = 3) -> pd.DataFrame:
    """
    Fetch `count` candles for `symbol` at the given `timeframe` ("4H", "1H", "15M").
    Returns a DataFrame with columns: epoch, open, high, low, close, time
    """
    granularity = GRANULARITY[timeframe]
    last_err = None

    for attempt in range(retries):
        try:
            ws = websocket.create_connection(WS_URL, timeout=15)
            request = {
                "ticks_history": symbol,
                "adjust_start_time": 1,
                "count": count,
                "end": "latest",
                "start": 1,
                "style": "candles",
                "granularity": granularity,
            }
            ws.send(json.dumps(request))
            response = json.loads(ws.recv())
            ws.close()

            if "error" in response:
                raise RuntimeError(response["error"]["message"])

            candles = response.get("candles", [])
            if not candles:
                raise RuntimeError(f"No candle data returned for {symbol} {timeframe}")

            df = pd.DataFrame(candles)
            df = df.rename(columns={"epoch": "epoch"})
            df["open"] = df["open"].astype(float)
            df["high"] = df["high"].astype(float)
            df["low"] = df["low"].astype(float)
            df["close"] = df["close"].astype(float)
            df["time"] = pd.to_datetime(df["epoch"], unit="s", utc=True)
            return df.reset_index(drop=True)

        except Exception as e:
            last_err = e
            time.sleep(2)

    raise RuntimeError(f"Failed to fetch {symbol} {timeframe} after {retries} attempts: {last_err}")
              
