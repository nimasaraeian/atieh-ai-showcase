@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo  Atieh AI - Folder Watcher
echo ========================================
echo.
echo Watching: C:\AtiehAI\incoming
echo API must be running on http://127.0.0.1:8000
echo Press Ctrl+C to stop
echo.

python watchers/folder_watcher.py

pause
