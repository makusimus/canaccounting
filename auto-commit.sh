#!/bin/bash
# Auto-commit workspace - runs without AI, just git
cd /home/makusimus/.openclaw/workspace

# Check for changes
changes=$(git status --short)
if [ -z "$changes" ]; then
  echo "No changes to commit."
  exit 0
fi

# Commit and push
git add -A
git commit -m "📝 Daily auto-commit — $(date +%Y-%m-%d)"
git push 2>/dev/null || echo "Push failed (no remote configured)"

echo "Committed:"
echo "$changes"
