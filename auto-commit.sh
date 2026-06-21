#!/bin/bash
# Auto-commit workspace + accounting - runs without AI, just git

# === Main workspace ===
cd /home/makusimus/.openclaw/workspace

changes=$(git status --short)
if [ -n "$changes" ]; then
  git add -A
  git commit -m "📝 Daily auto-commit — $(date +%Y-%m-%d)"
  git push 2>/dev/null || echo "Push failed (no remote configured)"
  echo "Workspace committed:"
  echo "$changes"
else
  echo "Workspace: No changes."
fi

# === Accounting repo ===
cd /home/makusimus/.openclaw/workspace/accounting

changes=$(git status --short)
if [ -n "$changes" ]; then
  git add -A
  git commit -m "📝 Accounting auto-commit — $(date +%Y-%m-%d)"
  git push 2>/dev/null || echo "Accounting push failed (no remote configured)"
  echo "Accounting committed:"
  echo "$changes"
else
  echo "Accounting: No changes."
fi
