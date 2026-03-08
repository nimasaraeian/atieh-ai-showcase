# bench_top_patients.ps1
# Measures response time for GET /ai/top-patients?limit=20&days=365
# Runs multiple iterations and reports min / avg / max / p95.
#
# Usage:
#   .\scripts\bench_top_patients.ps1
#   .\scripts\bench_top_patients.ps1 -BaseUrl http://127.0.0.1:8000 -Iterations 5

param(
    [string]$BaseUrl    = "http://127.0.0.1:8000",
    [int]   $Iterations = 5,
    [int]   $TimeoutSec = 120
)

$ErrorActionPreference = "Stop"

$Url = "$BaseUrl/ai/top-patients?limit=20&days=365"

function Write-Sep { Write-Host ("-" * 62) }
function Write-Header {
    Write-Host ""
    Write-Host ("=" * 62)
    Write-Host "  bench_top_patients.ps1"
    Write-Host "  URL        : $Url"
    Write-Host "  Iterations : $Iterations"
    Write-Host ("=" * 62)
    Write-Host ""
}

Write-Header

# --- confirm server is reachable before benchmarking ---
Write-Host "  [*] Checking server ..."
try {
    $ping = Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get -TimeoutSec 10
    Write-Host "  [OK] Server online  status=$($ping.status)  version=$($ping.version)"
} catch {
    Write-Host "  [FAIL] Server not reachable at $BaseUrl"
    Write-Host "         $_"
    exit 1
}
Write-Host ""
Write-Sep

# --- benchmark loop ---
$timings = @()
$firstBody = $null

for ($i = 1; $i -le $Iterations; $i++) {
    Write-Host -NoNewline "  Run $i/$Iterations  ..."

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $resp = Invoke-RestMethod -Uri $Url -Method Get -TimeoutSec $TimeoutSec
        $sw.Stop()
        $ms = $sw.ElapsedMilliseconds
        $timings += $ms

        $count = if ($resp.items) { $resp.items.Count } else { "?" }
        Write-Host "  ${ms}ms  (items=$count)"

        if ($null -eq $firstBody) { $firstBody = $resp }
    } catch {
        $sw.Stop()
        Write-Host "  FAILED after $($sw.ElapsedMilliseconds)ms"
        Write-Host "  ERROR: $_"
        exit 1
    }

    # small cooldown between runs to avoid DB cache warm-up bias
    if ($i -lt $Iterations) { Start-Sleep -Milliseconds 500 }
}

Write-Sep

# --- compute statistics ---
$sorted = $timings | Sort-Object
$minMs  = $sorted[0]
$maxMs  = $sorted[-1]
$avgMs  = [math]::Round(($timings | Measure-Object -Sum).Sum / $timings.Count, 1)

# p95: index = ceil(0.95 * N) - 1  (0-based)
$p95Idx = [math]::Max(0, [math]::Ceiling(0.95 * $sorted.Count) - 1)
$p95Ms  = $sorted[$p95Idx]

Write-Host ""
Write-Host "  BENCHMARK RESULTS  ($Iterations runs)"
Write-Host ("  " + ("-" * 38))
Write-Host ("  Min  : {0,6} ms" -f $minMs)
Write-Host ("  Avg  : {0,6} ms" -f $avgMs)
Write-Host ("  P95  : {0,6} ms" -f $p95Ms)
Write-Host ("  Max  : {0,6} ms" -f $maxMs)
Write-Host ""

# --- spot-check first response shape ---
if ($null -ne $firstBody) {
    Write-Host "  RESPONSE SHAPE CHECK"
    Write-Sep

    $days  = $firstBody.days
    $lim   = $firstBody.limit
    $items = $firstBody.items
    $gen   = $firstBody.generated_at

    Write-Host "  days         = $days"
    Write-Host "  limit        = $lim"
    Write-Host "  generated_at = $gen"
    Write-Host "  items.Count  = $($items.Count)"
    Write-Host ""

    if ($items.Count -gt 0) {
        Write-Host "  Top-5 scored patients:"
        $items | Select-Object -First 5 | ForEach-Object {
            Write-Host ("    patient_id={0,-8} history_score={1}" -f $_.patient_id, $_.history_score)
        }
    } else {
        Write-Host "  WARNING: items array is empty. Check days/limit params."
    }
}

Write-Host ""
Write-Host ("=" * 62)

# --- threshold advisory ---
if ($avgMs -gt 5000) {
    Write-Host "  ADVISORY: avg $avgMs ms exceeds 5s target."
    Write-Host "  Consider narrowing ?days= or adding a composite index"
    Write-Host "  on (appointment_date, patient_id) in appointments."
} elseif ($avgMs -gt 2000) {
    Write-Host "  NOTE: avg $avgMs ms is acceptable but approaching 2s."
    Write-Host "  Verify idx_appointments_date index is present."
} else {
    Write-Host "  GOOD: avg $avgMs ms is within acceptable range."
}

Write-Host ("=" * 62)
Write-Host ""
