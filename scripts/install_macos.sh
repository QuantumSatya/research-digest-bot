#!/bin/bash
# Run the Research Digest Bot every day at 09:00 (and at login / wake if 09:00 was missed).
# The weekly report itself is made on the report_weekday set in config.ini.
set -e
BOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-$(command -v python3)}"
HOUR="${HOUR:-9}"; MINUTE="${MINUTE:-0}"
LABEL="io.github.research-digest-bot"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array><string>$PY</string><string>$BOT_DIR/digest.py</string></array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>$HOUR</integer><key>Minute</key><integer>$MINUTE</integer></dict>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$HOME/Library/Logs/research-digest-bot.log</string>
  <key>StandardErrorPath</key><string>$HOME/Library/Logs/research-digest-bot.log</string>
</dict>
</plist>
PLIST
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Installed. Runs daily at $(printf %02d:%02d "$HOUR" "$MINUTE") with $PY"
echo "Check:  launchctl list | grep research-digest   (middle number 0 = last run OK)"
echo "Log:    ~/Library/Logs/research-digest-bot.log"
