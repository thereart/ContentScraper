@echo off
title Content Scraper v2
rem Double-click to start. Close this window to stop the scraper.
cd /d "%~dp0"
where python >nul 2>&1 || (echo Python is not installed. Get it from https://www.python.org/downloads/ & pause & exit /b 1)
python -c "import anthropic" 2>nul || python -m pip install -q anthropic
python ui.py
rem Only reached if the server stops with an error, e.g. port 8001 already in use.
pause
