#!/bin/bash
# Mac launcher: double-click to start. Close this window to stop the scraper.
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
    echo "Python is not installed. Get it from https://www.python.org/downloads/"
    read -n 1 -s -r -p "Press any key to close"
    exit 1
fi
python3 -c "import anthropic" 2>/dev/null || python3 -m pip install -q anthropic
python3 ui.py
# Only reached if the server stops with an error, e.g. port 8001 already in use.
read -n 1 -s -r -p "Press any key to close"
