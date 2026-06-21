#!/bin/bash
# Track new OPEN programs on UCalgary study abroad page
# Runs Mon-Fri via cron, alerts on Telegram when new OPEN lines appear

URL="https://www.ucalgary.ca/international/study-abroad/program-finder"
DIR="/home/makusimus/.openclaw/workspace/accounting/ucalgary_tracker"
mkdir -p "$DIR"

TODAY=$(date +%Y-%m-%d)
CACHE="$DIR/page.html"
PREVIOUS="$DIR/open_lines.txt"
CURRENT="$DIR/open_current_$TODAY.txt"
LAST_RUN_FILE="$DIR/last_success.txt"

# Fetch page with proper browser-like headers
curl -sL --max-time 15 \
  -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" \
  "$URL" > "$CACHE"

# Verify we got actual HTML (not an error page)
if ! grep -qi "program-finder\|study abroad\|uclas\|accordion" "$CACHE" 2>/dev/null; then
  echo "ERROR: Page fetch failed or returned unexpected content"
  if [ -f "$CURRENT" ] && [ -s "$CURRENT" ]; then
    echo "Using existing $CURRENT snapshot"
  fi
  exit 1
fi

# Extract OPEN program names with country context
python3 << 'PYEOF' > "$CURRENT"
import re

with open('/home/makusimus/.openclaw/workspace/accounting/ucalgary_tracker/page.html', 'r') as f:
    html = f.read()

# Find all accordion items (country level) that contain OPEN
# Structure: <h4>Country</h4> ... <strong>OPEN...</strong>
pattern = r'<h4[^>]*>.*?<a[^>]*>(.*?)</a>.*?</h4>(.*?)(?=<h4|<div class="minimal-accordion-item-group|</div>\s*</div>\s*</div>)'
items = re.findall(pattern, html, re.DOTALL)

results = []
for country, content in items:
    country = re.sub(r'<[^>]+>', '', country).strip()
    opens = re.findall(r'<strong>OPEN[^<]*</strong>.*?<a[^>]*>.*?<strong>(.*?)</strong>', content, re.DOTALL)
    for uni in opens:
        uni = re.sub(r'<[^>]+>', '', uni).strip()
        results.append(f'{country}|{uni}')

for r in sorted(results):
    print(r)
PYEOF

OPEN_COUNT=$(wc -l < "$CURRENT")

# Ensure consistent sort order for comm comparisons
export LC_ALL=C

# First run — just save and exit
if [ ! -f "$PREVIOUS" ]; then
  cp "$CURRENT" "$PREVIOUS"
  date > "$LAST_RUN_FILE"
  echo "First run — $OPEN_COUNT OPEN programs saved. No alerts."
  exit 0
fi

# Check if baseline is stale (>7 days old) — if so, refresh silently
if [ -f "$PREVIOUS" ]; then
  PREV_AGE=$(( ($(date +%s) - $(stat -c '%Y' "$PREVIOUS")) / 86400 ))
  if [ "$PREV_AGE" -gt 7 ]; then
    cp "$CURRENT" "$PREVIOUS"
    date > "$LAST_RUN_FILE"
    echo "Baseline refreshed ($PREV_AGE days old). $OPEN_COUNT OPEN programs. No alerts."
    exit 0
  fi
fi

# Compare with previous
NEW_LINES=$(comm -23 "$CURRENT" "$PREVIOUS")

if [ -z "$NEW_LINES" ]; then
  echo "No new OPEN programs. ($OPEN_COUNT total)"
  date > "$LAST_RUN_FILE"
  exit 0
fi

# Build the message and send via Python (handles newlines and Markdown properly)
python3 << PYEOF
import requests

new_lines = """$NEW_LINES"""

programs = ""
for line in new_lines.strip().split("\n"):
    if "|" in line:
        parts = line.split("|", 1)
        country = parts[0].strip()
        uni = parts[1].strip()
        programs += "• " + uni + " — " + country + "\n"

msg = (
    "🎓 **New UCalgary Exchange Programs OPEN!**\n\n"
    "New program(s) opened:\n"
    + programs + "\n"
    + "Check: https://www.ucalgary.ca/international/study-abroad/program-finder"
)

r = requests.post(
    "https://api.telegram.org/bot8610237196:AAG1uTcldz-EQ5flGtl3OfI5hiDnPI8cPg8/sendMessage",
    json={
        "chat_id": 387284187,
        "text": msg,
        "parse_mode": "Markdown"
    },
    timeout=10
)
print(f"Telegram sent: {r.status_code}, ok: {r.json().get('ok')}")
PYEOF

echo "Alert sent! New programs:"
echo "$NEW_LINES"

# Update saved list
cp "$CURRENT" "$PREVIOUS"
date > "$LAST_RUN_FILE"
