@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo  Atieh AI - API Server
echo ========================================
echo.
echo Starting FastAPI on http://127.0.0.1:8000
echo Press Ctrl+C to stop
echo.

python -m uvicorn main:app --host 127.0.0.1 --port 8000

pause
