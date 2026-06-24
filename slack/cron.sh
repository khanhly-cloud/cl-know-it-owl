#!/bin/zsh
# Know-It-Owl cron entrypoint (local cron). Usage: cron.sh announce|resolve
# Logs to /tmp/owl-cron.log. Runs the mechanical autorun (no Claude, no tokens).
cd "/Users/andyly/Desktop/CLAUDE GENERAL/cl-did-you-know" || exit 1
echo "[$(date '+%Y-%m-%d %H:%M:%S')] cron $1" >> /tmp/owl-cron.log
/usr/bin/python3 slack/autorun.py "$1" >> /tmp/owl-cron.log 2>&1
