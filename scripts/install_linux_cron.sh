#!/bin/bash
# Adds a daily cron job (09:00) for the Research Digest Bot. Re-running replaces it.
set -e
BOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-$(command -v python3)}"
LINE="0 9 * * * cd \"$BOT_DIR\" && \"$PY\" digest.py >> \"$HOME/.research-digest-bot.log\" 2>&1 # research-digest-bot"
( crontab -l 2>/dev/null | grep -v '# research-digest-bot' ; echo "$LINE" ) | crontab -
echo "Installed cron job:"; crontab -l | grep research-digest-bot
echo "Note: cron does not catch up missed runs; anacron or a systemd timer with Persistent=true does."
