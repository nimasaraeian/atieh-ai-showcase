$port = 8001

$listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue

if ($listener) {
  $procId = $listener.OwningProcess
  Write-Host "Port $port is in use by PID $procId. Stopping it..."
  Stop-Process -Id $procId -Force
  Start-Sleep -Seconds 1
}

$env:ENABLE_DEBUG_ENDPOINTS="1"
python -m uvicorn main:app --host 127.0.0.1 --port $port --reload --log-level debug