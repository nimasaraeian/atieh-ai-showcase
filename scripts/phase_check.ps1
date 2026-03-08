# phase_check.ps1 - Server health + DB + score endpoint verification
# ASCII-safe, PowerShell-native (no bash heredoc)

Set-StrictMode -Off
$ErrorActionPreference = "SilentlyContinue"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  PHASE CHECK - Atieh Clinic API Verification" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ----------------------------------------------------------------
# STEP 1: Kill any process on port 8000 and 8001
# ----------------------------------------------------------------
Write-Host "[1] Clearing ports 8000 and 8001..." -ForegroundColor Yellow

foreach ($port in @(8000, 8001)) {
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($conn) {
        $pid_ = $conn.OwningProcess
        Write-Host "    Port $port in use by PID $pid_ - killing..." -ForegroundColor DarkYellow
        taskkill /PID $pid_ /F 2>&1 | Out-Null
        Start-Sleep -Seconds 1
        Write-Host "    Port $port cleared." -ForegroundColor Green
    } else {
        Write-Host "    Port $port is free." -ForegroundColor Green
    }
}
Write-Host ""

# ----------------------------------------------------------------
# STEP 2: Start uvicorn in background job
# ----------------------------------------------------------------
Write-Host "[2] Starting uvicorn on port 8000..." -ForegroundColor Yellow

$repoRoot = Split-Path -Parent $PSScriptRoot

$env:CRM_MODE = "mock"
$env:ENABLE_DEBUG_ENDPOINTS = "1"

$serverJob = Start-Job -ScriptBlock {
    param($root)
    Set-Location $root
    $env:CRM_MODE = "mock"
    $env:ENABLE_DEBUG_ENDPOINTS = "1"
    python -m uvicorn main:app --host 127.0.0.1 --port 8000 2>&1
} -ArgumentList $repoRoot

Write-Host "    Server job started (Job ID: $($serverJob.Id))" -ForegroundColor Green
Write-Host ""

# ----------------------------------------------------------------
# STEP 3: Poll /openapi.json until reachable (max 10s)
# ----------------------------------------------------------------
Write-Host "[3] Waiting for server to become reachable..." -ForegroundColor Yellow

$serverPort = $null
$serverReachable = $false
$maxWait = 10
$waited = 0

while ($waited -lt $maxWait) {
    Start-Sleep -Seconds 1
    $waited++

    foreach ($p in @(8000, 8001)) {
        try {
            $resp = Invoke-RestMethod -Uri "http://127.0.0.1:$p/openapi.json" -TimeoutSec 2 -ErrorAction Stop
            $serverPort = $p
            $serverReachable = $true
            break
        } catch {
            # not yet
        }
    }

    if ($serverReachable) { break }
    Write-Host "    Waiting... ($waited/$maxWait)" -ForegroundColor DarkGray
}

if ($serverReachable) {
    Write-Host "    Server reachable on port $serverPort after ${waited}s" -ForegroundColor Green
} else {
    Write-Host "    [WARN] Server not reachable after ${maxWait}s. Continuing with checks..." -ForegroundColor Red
    $serverPort = 8000
}
Write-Host ""

# ----------------------------------------------------------------
# STEP 4: Dump routes containing "debug" or "score"
# ----------------------------------------------------------------
Write-Host "[4] Routes containing 'debug' or 'score':" -ForegroundColor Yellow

try {
    $openapi = Invoke-RestMethod -Uri "http://127.0.0.1:$serverPort/openapi.json" -TimeoutSec 5 -ErrorAction Stop
    $matchedRoutes = @()
    foreach ($path in $openapi.paths.PSObject.Properties) {
        $routePath = $path.Name
        if ($routePath -match "debug|score") {
            foreach ($method in $path.Value.PSObject.Properties) {
                $matchedRoutes += "$($method.Name.ToUpper()) $routePath"
            }
        }
    }
    if ($matchedRoutes.Count -gt 0) {
        foreach ($r in $matchedRoutes) {
            Write-Host "    $r" -ForegroundColor White
        }
    } else {
        Write-Host "    [WARN] No debug/score routes found." -ForegroundColor Red
    }
} catch {
    Write-Host "    [ERROR] Could not fetch openapi.json: $_" -ForegroundColor Red
}
Write-Host ""

# ----------------------------------------------------------------
# STEP 5: List *.db files in repo root
# ----------------------------------------------------------------
Write-Host "[5] DB files in repo root:" -ForegroundColor Yellow

$dbFiles = Get-ChildItem -Path $repoRoot -Filter "*.db" -Force -ErrorAction SilentlyContinue
if (-not $dbFiles) {
    Write-Host "    [WARN] No .db files found in $repoRoot" -ForegroundColor Red
} else {
    foreach ($db in $dbFiles) {
        $sizeKB = [math]::Round($db.Length / 1KB, 1)
        Write-Host ("    {0,-40} {1,8} KB   {2}" -f $db.Name, $sizeKB, $db.LastWriteTime) -ForegroundColor White
    }
}
Write-Host ""

# ----------------------------------------------------------------
# STEP 6: Per-DB: table count, stg_appointments check, row/error counts
# ----------------------------------------------------------------
Write-Host "[6] SQLite DB inspection:" -ForegroundColor Yellow

Add-Type -AssemblyName "System.Data" -ErrorAction SilentlyContinue

function Invoke-SQLite {
    param([string]$dbPath, [string]$sql)
    try {
        $conn = New-Object System.Data.SQLite.SQLiteConnection("Data Source=$dbPath;Version=3;Read Only=True;")
        $conn.Open()
        $cmd = $conn.CreateCommand()
        $cmd.CommandText = $sql
        $reader = $cmd.ExecuteReader()
        $results = @()
        while ($reader.Read()) {
            $row = @{}
            for ($i = 0; $i -lt $reader.FieldCount; $i++) {
                $row[$reader.GetName($i)] = $reader.GetValue($i)
            }
            $results += $row
        }
        $reader.Close()
        $conn.Close()
        return $results
    } catch {
        return $null
    }
}

# Fallback: use sqlite3.exe command line if available
function Invoke-SQLite3CLI {
    param([string]$dbPath, [string]$sql)
    $sqlite3 = Get-Command "sqlite3" -ErrorAction SilentlyContinue
    if (-not $sqlite3) { return $null }
    $output = echo $sql | sqlite3 $dbPath 2>&1
    return $output
}

# Use Python sqlite3 as the most reliable fallback on Windows
function Invoke-SQLitePython {
    param([string]$dbPath, [string]$sql)
    $escaped = $sql -replace '"', '\"'
    $py = @"
import sqlite3, sys
try:
    conn = sqlite3.connect(r'$dbPath')
    cur = conn.cursor()
    cur.execute("$escaped")
    rows = cur.fetchall()
    for row in rows:
        print('|'.join(str(x) for x in row))
    conn.close()
except Exception as e:
    print('ERROR:' + str(e), file=sys.stderr)
"@
    $result = $py | python - 2>&1
    return $result
}

$dbSummary = @{}

if (-not $dbFiles) {
    Write-Host "    No DB files to inspect." -ForegroundColor DarkGray
} else {
    foreach ($db in $dbFiles) {
        Write-Host ("  --> {0}" -f $db.FullName) -ForegroundColor Cyan

        # Table count
        $tableCountRaw = Invoke-SQLitePython -dbPath $db.FullName -sql "SELECT COUNT(1) FROM sqlite_master WHERE type='table'"
        $tableCount = if ($tableCountRaw -and $tableCountRaw -notmatch "^ERROR") { $tableCountRaw.Trim() } else { "?" }
        Write-Host ("      Tables: {0}" -f $tableCount) -ForegroundColor White

        # List tables
        $tablesRaw = Invoke-SQLitePython -dbPath $db.FullName -sql "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        if ($tablesRaw -and $tablesRaw -notmatch "^ERROR") {
            Write-Host ("      Table names: {0}" -f ($tablesRaw -join ", ")) -ForegroundColor Gray
        }

        # Check stg_appointments
        $hasStg = Invoke-SQLitePython -dbPath $db.FullName -sql "SELECT COUNT(1) FROM sqlite_master WHERE type='table' AND name='stg_appointments'"
        if ($hasStg -and $hasStg.Trim() -eq "1") {
            Write-Host "      stg_appointments: EXISTS" -ForegroundColor Green

            $rowCount = Invoke-SQLitePython -dbPath $db.FullName -sql "SELECT COUNT(1) FROM stg_appointments"
            Write-Host ("      stg_appointments rows: {0}" -f $rowCount.Trim()) -ForegroundColor White

            $errCount = Invoke-SQLitePython -dbPath $db.FullName -sql "SELECT COUNT(1) FROM stg_appointments WHERE parse_status='error'"
            Write-Host ("      stg_appointments parse_status='error': {0}" -f $errCount.Trim()) -ForegroundColor White

            $dbSummary[$db.Name] = [int]($rowCount.Trim())
        } else {
            Write-Host "      stg_appointments: NOT FOUND" -ForegroundColor DarkGray
            $dbSummary[$db.Name] = 0
        }
        Write-Host ""
    }
}

# ----------------------------------------------------------------
# STEP 7: POST to score endpoints
# ----------------------------------------------------------------
Write-Host "[7] Testing score endpoints..." -ForegroundColor Yellow

$scoreBody = '{"urgency_score":0.8,"financial_score":0.7,"availability_score":0.9,"complexity_fit_score":0.6}'
$headers = @{ "Content-Type" = "application/json" }

$scoreEndpoints = @(
    "http://127.0.0.1:$serverPort/debug/score",
    "http://127.0.0.1:$serverPort/api/debug/score"
)

$workingScoreEndpoint = $null

foreach ($ep in $scoreEndpoints) {
    try {
        $result = Invoke-RestMethod -Uri $ep -Method POST -Body $scoreBody -Headers $headers -TimeoutSec 5 -ErrorAction Stop
        Write-Host ("    [OK] {0}" -f $ep) -ForegroundColor Green
        Write-Host ("         total_score = {0}" -f $result.total_score) -ForegroundColor White
        Write-Host ("         urgency={0} financial={1} availability={2} complexity={3}" -f `
            $result.urgency_score, $result.financial_score, $result.availability_score, $result.complexity_fit_score) -ForegroundColor Gray
        $workingScoreEndpoint = $ep
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Write-Host ("    [FAIL] {0}  (HTTP {1})" -f $ep, $statusCode) -ForegroundColor Red
    }
}
Write-Host ""

# ----------------------------------------------------------------
# STEP 8: Compact summary
# ----------------------------------------------------------------
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  SUMMARY" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

Write-Host ("  Server OK       : {0}" -f $(if ($serverReachable) { "YES" } else { "NO" })) -ForegroundColor $(if ($serverReachable) { "Green" } else { "Red" })
Write-Host ("  Active port     : {0}" -f $serverPort) -ForegroundColor White
Write-Host ("  Score endpoint  : {0}" -f $(if ($workingScoreEndpoint) { $workingScoreEndpoint } else { "NONE WORKED" })) -ForegroundColor $(if ($workingScoreEndpoint) { "Green" } else { "Red" })

# Identify most active DB
if ($dbSummary.Count -gt 0) {
    $activeDb = ($dbSummary.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 1).Key
    Write-Host ("  Active DB       : {0} (most rows in stg_appointments)" -f $activeDb) -ForegroundColor White
} else {
    Write-Host "  Active DB       : UNKNOWN (no DB files found)" -ForegroundColor Red
    $activeDb = "atieh_clinic.db (expected path: repo root)"
}

Write-Host ""
Write-Host "  Next actions:" -ForegroundColor Yellow

if (-not $serverReachable) {
    Write-Host "    - Server did not start. Check for import errors: python -c 'import main'" -ForegroundColor DarkYellow
    Write-Host "    - Run manually: python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload" -ForegroundColor DarkYellow
}
if (-not $workingScoreEndpoint) {
    Write-Host "    - Score endpoint failed. Ensure ENABLE_DEBUG_ENDPOINTS=1 is set before starting." -ForegroundColor DarkYellow
}
if ($dbSummary.Count -eq 0) {
    Write-Host "    - No DB found at repo root. Check DATABASE_URL env var or let app create it on first run." -ForegroundColor DarkYellow
}
if ($serverReachable -and $workingScoreEndpoint -and $dbSummary.Count -gt 0) {
    Write-Host "    - All checks passed. Ready to proceed with integration testing." -ForegroundColor Green
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Clean up background job
Stop-Job -Job $serverJob -ErrorAction SilentlyContinue
Remove-Job -Job $serverJob -ErrorAction SilentlyContinue
