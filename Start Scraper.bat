@echo off
title Content Scraper
rem Double-click to start. Close this window to stop the scraper.
cd /d "%~dp0"
where python >nul 2>&1 || (echo Python is not installed. Get it from https://www.python.org/downloads/ & pause & exit /b 1)
python ui.py
rem Only reached if the server stops with an error, e.g. port 8000 already in use.
pause
