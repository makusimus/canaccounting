#!/usr/bin/env python3
"""
BTC Weekly Summary — system crontab version (zero LLM tokens)
Replaces the old OpenClaw cron job. Runs Sundays.
"""

import json
import os
import urllib.request
import sys
from datetime import datetime, timezone

CHAT_ID = "387284187"
STATE_FILE = os.path.expanduser("~/.openclaw/workspace/memory/btc-tracker-state.json")

# Get bot token
TOKEN_FILE = "/tmp/.tg_bot_token_cache"
if os.path.exists(TOKEN_FILE):
    with open(TOKEN_FILE) as f:
        BOT_TOKEN = f.read().strip()
else:
    with open(os.path.expanduser("~/.openclaw/openclaw.json")) as f:
        c = json.load(f)
    BOT_TOKEN = c["channels"]["telegram"]["botToken"]


def fetch_json(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        print("  Fetch failed: " + str(e), file=sys.stderr)
        return None


def send_telegram(msg):
    url = "https://api.telegram.org/bot" + BOT_TOKEN + "/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown",
    }
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode(),
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print("  Telegram send failed: " + str(e), file=sys.stderr)


def fmt_price(n):
    return "${:,}".format(n)


def main():
    print("BTC Weekly Summary...", file=sys.stderr)

    # 1. BTC Price + FnG
    price_data = fetch_json("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd")
    if not price_data:
        print("  Price fetch failed, aborting", file=sys.stderr)
        return
    btc_price = int(price_data.get("bitcoin", {}).get("usd", 0))
    if btc_price == 0:
        return

    fng_data = fetch_json("https://api.alternative.me/fng/")
    fng = int(fng_data["data"][0]["value"]) if fng_data and "data" in fng_data else 0

    # 2. Blockchain stats
    chain_data = fetch_json("https://blockchain.info/stats?format=json")
    if chain_data:
        hash_rate_gh = chain_data.get("hash_rate", 0)
        hash_rate_eh = round(hash_rate_gh / 1_000_000_000, 1) if hash_rate_gh else 0
        difficulty = chain_data.get("difficulty", 0)
        totalbc_sat = chain_data.get("totalbc", 0)
        circ_supply = round(totalbc_sat / 100_000_000, 1) if totalbc_sat else 0
        n_tx = chain_data.get("n_tx", 0)
        total_fees_sat = chain_data.get("total_fees_btc", 0)
        total_fees_btc = round(abs(total_fees_sat) / 100_000_000, 4) if total_fees_sat else 0
        ath_pct = round(btc_price / 126080 * 100, 1)
        market_cap = round(btc_price * circ_supply / 1_000_000_000, 2) if circ_supply else 0
        s2f = round(circ_supply / 0.164250, 0) if circ_supply else 0
    else:
        hash_rate_eh = 0
        difficulty = 0
        circ_supply = 0
        n_tx = 0
        total_fees_btc = 0
        ath_pct = 0
        market_cap = 0
        s2f = 0

    # 3. Read state for thresholds
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
    except:
        state = {"thresholdsTriggered": []}
    triggered = state.get("thresholdsTriggered", [])

    # 4. Check thresholds (same logic as daily)
    new_alert = ""
    if "price_55k" not in triggered and btc_price <= 55000:
        triggered.append("price_55k")
        new_alert = "price_55k - First DCA zone (" + fmt_price(btc_price) + ")"
    elif "price_52k" not in triggered and btc_price <= 52000:
        triggered.append("price_52k")
        new_alert = "price_52k - Second DCA zone (" + fmt_price(btc_price) + ")"
    elif "price_48k" not in triggered and btc_price <= 48000:
        triggered.append("price_48k")
        new_alert = "price_48k - Aggressive buy zone (" + fmt_price(btc_price) + ")"
    elif "fng_extreme" not in triggered and fng <= 10:
        triggered.append("fng_extreme")
        new_alert = "fng_extreme - Capitulation zone (FnG: " + str(fng) + ")"

    # Update state
    state["lastCheck"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state["lastPrice"] = btc_price
    state["lastFng"] = fng
    if hash_rate_eh:
        state["lastHashrate"] = hash_rate_eh
    if difficulty:
        state["lastDifficulty"] = difficulty
    if circ_supply:
        state["lastCirculatingSupply"] = circ_supply
    state["thresholdsTriggered"] = triggered
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

    # 5. Classify FnG
    if fng <= 20:
        fng_class = "Extreme Fear"
    elif fng <= 40:
        fng_class = "Fear"
    elif fng <= 60:
        fng_class = "Neutral"
    elif fng <= 80:
        fng_class = "Greed"
    else:
        fng_class = "Extreme Greed"

    # 6. Build summary
    threshold_str = ", ".join(triggered) if triggered else "None triggered yet"
    if new_alert:
        new_alert_str = chr(9888) + " New this week: **" + new_alert + "**"
    else:
        new_alert_str = "No new thresholds this week."

    lines = []
    lines.append(chr(128202) + " *BTC Weekly Report*")
    lines.append("")
    lines.append("**Price:** " + fmt_price(btc_price) + " (" + str(ath_pct) + "% from ATH)")
    lines.append("**Fear & Greed:** " + str(fng) + " - " + fng_class)
    lines.append("**Hashrate:** " + "{:,}".format(hash_rate_eh) + " EH/s")
    lines.append("**Difficulty:** " + "{:,}".format(difficulty))
    lines.append("**Circulating Supply:** " + "{:,}".format(circ_supply) + " BTC")
    lines.append("**Market Cap:** " + fmt_price(market_cap) + "B")
    lines.append("**Stock-to-Flow:** " + "{:,.0f}".format(s2f))
    lines.append("**24h TX:** " + "{:,}".format(n_tx) + " (fees: " + str(total_fees_btc) + " BTC)")
    lines.append("")
    lines.append("**Thresholds triggered:** " + threshold_str)
    lines.append(new_alert_str)
    lines.append("")
    lines.append(chr(128308) + " *Manual check reminder:*")
    lines.append("MVRV Z-Score -> charts.bitbo.io")
    lines.append("Puell Multiple -> same")
    lines.append("Z-Score < 0 = historic bottom. Puell < 0.5 = miner capitulation.")
    lines.append("")
    lines.append(chr(129302) + " Generated by system script - no AI tokens used")

    summary = "\n".join(lines)

    # 7. Send
    send_telegram(summary)
    print("  Sent!", file=sys.stderr)


if __name__ == "__main__":
    main()
