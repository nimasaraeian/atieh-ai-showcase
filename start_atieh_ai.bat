@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo  Atieh AI - Starting API and Watcher
echo ========================================
echo.
echo Opening API server in new window...
start "Atieh AI - API" cmd /k "cd /d %~dp0 && python -m uvicorn main:app --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak >nul

echo Opening folder watcher in new window...
start "Atieh AI - Watcher" cmd /k "cd /d %~dp0 && python watchers/folder_watcher.py"

echo.
echo Both processes started. Close each window to stop.
pause
