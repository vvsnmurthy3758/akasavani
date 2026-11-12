@echo off
title Coqui TTS Web UI
cd /d "%~dp0"
".venv\Scripts\python.exe" "start_webui.py"
echo.
echo (You can close this window now.)
pause
