# Local development startup script (Windows PowerShell)
# ASCII-safe version - no emojis or Unicode symbols

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Atieh Clinic Scheduling AI - Local Run" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Generate mock data if not exists
if (-not (Test-Path "data\mock\patients.json")) {
    Write-Host "[*] Generating mock CRM data..." -ForegroundColor Yellow
    python scripts\generate_mock_crm_data.py --patients 200 --appointments 1000
    Write-Host ""
}

# Step 2: Set environment variables
$env:CRM_MODE = "mock"
$env:ENABLE_DEBUG_ENDPOINTS = "1"
Write-Host "[OK] CRM_MODE set to: mock" -ForegroundColor Green
Write-Host "[OK] ENABLE_DEBUG_ENDPOINTS set to: 1" -ForegroundColor Green
Write-Host ""

# Step 3: Run tests (optional)
if ($args -contains "--test") {
    Write-Host "[*] Running tests..." -ForegroundColor Yellow
    pytest tests/ -q
    Write-Host ""
}

# Step 4: Start server
Write-Host "[>>] Starting FastAPI server..." -ForegroundColor Green
Write-Host "     Server: http://127.0.0.1:8000" -ForegroundColor Gray
Write-Host "     Docs:   http://127.0.0.1:8000/docs" -ForegroundColor Gray
Write-Host ""
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
