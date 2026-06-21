# SMC Top-Down Scanner (4H → 1H → 15min)

Implements the top-down chart analysis framework: establish bias on 4H,
confirm it on 1H, time the entry on 15min. Runs as a GitHub Actions
single-pass job and sends Telegram alerts with a full confluence breakdown.

## How the framework maps to the code

| Timeframe | Role | Criteria checked |
|---|---|---|
| 4H | Direction / Key Levels / Supply & Demand | `determine_trend()`, `get_key_levels()`, `find_supply_demand_zone()` |
| 1H | Breaks / Trend confirm / Order Block / FVG | `detect_bos_choch()`, `find_order_blocks()`, `find_fair_value_gaps()` |
| 15min | Liquidity sweep / Reversal / Confirmation | `detect_liquidity_sweep()`, `detect_reversal_confirmation()` |

Each criterion is weighted and combined in `modules/confluence.py`. A
signal only fires when total confluence is **8/12 or higher**.

## Which criteria matter most (and why)

Not all eight criteria are equally predictive — that's why they're weighted
rather than treated as a simple checklist:

- **Highest weight (2 points each): 1H BOS/CHoCH, 1H Order Block, 15min liquidity sweep, 15min confirmation candle.** This is the core ICT entry model — price sweeps liquidity (induces stop-outs), breaks structure in your bias direction, and gives a clean reversal candle at a 1H OB/FVG. These four together are what actually time an entry.
- **Lower weight (1 point each): 4H direction, 4H key level, 4H supply/demand zone, 1H FVG.** These set up *context* — they tell you which direction to look and where price "should" react — but on their own they're too common to trade. A 4H uptrend with no 1H break and no 15min confirmation is just a watchlist item, not a trade.
- In practice: don't trade off 4H/1H context alone. Wait for the liquidity sweep + confirmation candle on 15min — that's the highest-probability part of the model, because it shows smart money has actually taken the stops and reversed before continuation.

This is standard SMC/ICT methodology, not financial advice — always backtest
on your specific synthetic indices before trading live, since their
volatility behaves differently from retail forex pairs.

## Step-by-step setup

1. **Create the repo.** Push this folder structure to a new GitHub repo (e.g. `smc-topdown-scanner`), or copy the files into your existing `deriv-smc-scanner` repo under a new module name.
2. **Add secrets.** In the repo: Settings → Secrets and variables → Actions → New repository secret. Add `TELEGRAM_TOKEN` (your bot token) and `TELEGRAM_CHAT_ID` (yours is `388117501` from your existing bots).
3. **Edit `SYMBOLS`** in `main.py` to the Deriv synthetic indices you want scanned (e.g. `R_75`, `R_100`, `1HZ100V`, etc.).
4. **Enable Actions.** Go to the Actions tab, enable workflows if prompted. The scanner runs every 15 minutes automatically via cron, and can also be triggered manually with "Run workflow."
5. **Watch your Telegram bot.** When confluence hits 8/12+, you'll get an alert showing the full checklist (which criteria passed/failed) so you can sanity-check the setup before entering.
6. **Tune the threshold.** If alerts are too frequent or too rare, adjust `SIGNAL_THRESHOLD` in `modules/confluence.py` (default 8 out of 12).
7. **Backtest first.** Before trusting live alerts, let it run a week logging to the Action's console output, and manually compare signals against what actually happened on the chart.

## Notes

- Uses Deriv's public WebSocket API (`wss://ws.derivws.com`, app_id `1089`) — no API key/auth needed for market data.
- Timestamps are converted to WAT (UTC+1) to match your other bots.
- `data/sent_signals.json` is committed back by the workflow to persist cooldowns between runs (4-hour default per symbol+direction, adjustable in `main.py`).
- 
