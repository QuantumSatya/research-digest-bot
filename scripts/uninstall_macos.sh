#!/bin/bash
LABEL="io.github.research-digest-bot"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
echo "Removed the background job. Your reports are untouched."
