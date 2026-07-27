#!/usr/bin/env bash
# BTC Bottom Watch — Daily Check (Mon-Fri)
# System crontab version — zero LLM token cost

set -euo pipefail

BOT_TOKEN_FILE="/tmp/.tg_bot_token_cache"
CHAT_ID="387284187"
STATE_FILE="$HOME/.openclaw/workspace/memory/btc-tracker-state.json"
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Get token
BOT_TOKEN=$(cat "$BOT_TOKEN_FILE" 2>/dev/null || python3 -c "
import json
c = json.load(open('$HOME/.openclaw/openclaw.json'))
print(c['channels']['telegram']['botToken'])
")

send_telegram() {
    local msg="$1"
    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d "chat_id=${CHAT_ID}" \
        -d "text=${msg}" \
        -d "parse_mode=Markdown" > /dev/null
}

# 1. Fetch BTC price
BTC_RAW=$(curl -s "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd")
BTC=$(echo "$BTC_RAW" | python3 -c "import sys,json; d=json.load(sys.stdin); print(int(d['bitcoin']['usd']))" 2>/dev/null || echo "")
[ -z "$BTC" ] && exit 0

# 2. Fetch Fear & Greed
FNG=$(curl -s "https://api.alternative.me/fng/" | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['value'])" 2>/dev/null || echo "0")

# 3-5. Check thresholds and update state
TFILE=$(mktemp)
python3 -c "
import json

BTC = $BTC
FNG = int('${FNG}' or 0)
STATE = '$STATE_FILE'
NOW = '$NOW'

with open(STATE) as f:
    state = json.load(f)

triggered = state.get('thresholdsTriggered', [])
alert = ''

if 'price_55k' not in triggered and BTC <= 55000:
    triggered.append('price_55k')
    alert = 'BTC Alert: First DCA Zone\nBTC dropped to \${:,}\nTrigger: price_55k — Buy \$1K DCA'.format(BTC)
elif 'price_52k' not in triggered and BTC <= 52000:
    triggered.append('price_52k')
    alert = 'BTC Alert: Second DCA Zone\nBTC at \${:,}\nTrigger: price_52k — Buy another \$1K DCA'.format(BTC)
elif 'price_48k' not in triggered and BTC <= 48000:
    triggered.append('price_48k')
    alert = 'BTC Alert: Strong Buy Zone\nBTC at \${:,}\nTrigger: price_48k — Aggressive buy zone'.format(BTC)
elif 'fng_extreme' not in triggered and FNG <= 10:
    triggered.append('fng_extreme')
    alert = 'BTC Alert: Capitulation Zone\nFear & Greed at {}\nTrigger: fng_extreme — Extreme fear'.format(FNG)

state['lastCheck'] = NOW
state['lastPrice'] = BTC
state['lastFng'] = FNG
state['thresholdsTriggered'] = triggered

with open(STATE, 'w') as f:
    json.dump(state, f, indent=2)

if alert:
    with open('$TFILE', 'w') as f:
        f.write(alert)
"
# Send alert if triggered
if [ -s "$TFILE" ]; then
    MSG=$(cat "$TFILE")
    send_telegram "$MSG"
fi
rm -f "$TFILE"
