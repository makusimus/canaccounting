#!/bin/bash
PRICE_FILE="/tmp/crypto_day_btc.txt"
DATE_FILE="/tmp/crypto_day_date.txt"
TODAY=$(date -u +%Y-%m-%d)

ALT=$(curl -s "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ripple,sui&vs_currencies=usd")
BTC=$(echo "$ALT" | python3 -c "import sys,json;print(json.load(sys.stdin)['bitcoin']['usd'])" 2>/dev/null)
[ -z "$BTC" ] && exit 0

# New day reset
if [ ! -f "$DATE_FILE" ] || [ "$(cat "$DATE_FILE")" != "$TODAY" ]; then
  echo "$BTC" > "$PRICE_FILE"
  echo "$TODAY" > "$DATE_FILE"
  rm -f /tmp/caf_*_$TODAY
  exit 0
fi

START=$(cat "$PRICE_FILE")
CHG=$(python3 -c "print(($BTC - $START) / $START * 100)")
ABS=$(python3 -c "print(abs($CHG))")

# 3% incremental thresholds
for T in 3 6 9 12 15 18 21 24 27 30; do
  python3 -c "exit(0 if $ABS >= $T else 1)" 2>/dev/null || break
  FLAG="/tmp/caf_${T}_${TODAY}"
  [ -f "$FLAG" ] && continue
  
  touch "$FLAG"
  DIR="up"; python3 -c "exit(0 if $BTC > $START else 1)" 2>/dev/null || DIR="down"
  
  MSG="BTC Alert: ${T}% from daily open"
  MSG="$MSG\nDaily open: \$$(printf '%.0f' $START)"
  MSG="$MSG\nNow: \$$(printf '%.0f' $BTC)"
  MSG="$MSG\nMove: $(printf '%.1f' $CHG)%"
  MSG="$MSG\n$DIR"
  
  curl -s -X POST "https://api.telegram.org/bot8610237196:AAG1uTcldz-EQ5flGtl3OfI5hiDnPI8cPg8/sendMessage" \
    -d "chat_id=387284187" -d "text=$(echo -e "$MSG")" -d "parse_mode=Markdown" > /dev/null 2>&1
  break
done
