# smoke_tests.ps1 - Fast API smoke test suite
# Fail-fast: exits with code 1 on first failure
# Usage: powershell -ExecutionPolicy Bypass -File scripts\smoke_tests.ps1 [-BaseUrl http://127.0.0.1:8000]

param(
    [string]$BaseUrl   = "http://127.0.0.1:8000",
    [int]$TimeoutSec   = 10
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Off

$passed  = 0
$failed  = 0
$t_suite = Get-Date

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Write-Sep {
    Write-Host ("-" * 62) -ForegroundColor DarkGray
}

function Mark-Pass {
    param([string]$label, [string]$detail = "")
    $script:passed++
    Write-Host "  [PASS] $label" -ForegroundColor Green
    if ($detail) { Write-Host "         $detail" -ForegroundColor Gray }
}

function Mark-Fail {
    param([string]$label, [string]$detail = "")
    $script:failed++
    Write-Host "  [FAIL] $label" -ForegroundColor Red
    if ($detail) { Write-Host "         $detail" -ForegroundColor DarkRed }
}

function Invoke-Check {
    param(
        [string]$Label,
        [string]$Uri,
        [array]$Assertions = @(),
        [bool]$FailFast = $true
    )

    Write-Sep
    Write-Host "  TEST : $Label" -ForegroundColor Cyan
    Write-Host "   GET  $Uri" -ForegroundColor DarkCyan

    $t0 = Get-Date
    try {
        $resp = Invoke-RestMethod -Uri $Uri -Method GET -TimeoutSec $TimeoutSec -ErrorAction Stop
        $ms   = [int]((Get-Date) - $t0).TotalMilliseconds
        Write-Host "        HTTP 200  ${ms}ms" -ForegroundColor DarkGray
    } catch {
        $ms     = [int]((Get-Date) - $t0).TotalMilliseconds
        $code   = $_.Exception.Response.StatusCode.value__
        $errMsg = "HTTP $code after ${ms}ms  $($_.Exception.Message)"
        Mark-Fail -Label $Label -Detail $errMsg
        if ($FailFast) {
            Write-Host ""
            Write-Host "  Fail-fast triggered. Aborting." -ForegroundColor Red
            exit 1
        }
        return
    }

    $allOk = $true

    foreach ($a in $Assertions) {
        $field    = $a.Field
        $expected = $a.Expected
        $op       = $a.Op

        # Resolve dotted field path on response object
        $actual = $resp
        foreach ($part in ($field -split "\.")) {
            if ($null -eq $actual) { break }
            $actual = $actual.$part
        }

        $ok = switch ($op) {
            "eq"       { $actual -eq $expected }
            "ne"       { $actual -ne $expected }
            "gt"       { $actual -gt $expected }
            "ge"       { $actual -ge $expected }
            "lt"       { $actual -lt $expected }
            "contains" { "$actual" -match [regex]::Escape("$expected") }
            "notnull"  { $null -ne $actual -and "$actual" -ne "" }
            "exists"   { $null -ne $actual }
            default    { $false }
        }

        if ($ok) {
            Mark-Pass -Label "$field $op $expected" -Detail "actual=$actual"
        } else {
            Mark-Fail -Label "$field $op $expected" -Detail "actual=$actual"
            $allOk = $false
        }
    }

    # No assertions given -> 200 itself is a pass
    if ($Assertions.Count -eq 0) {
        Mark-Pass -Label $Label
    }

    if ((-not $allOk) -and $FailFast) {
        Write-Host ""
        Write-Host "  Fail-fast triggered. Aborting." -ForegroundColor Red
        exit 1
    }
}

# ---------------------------------------------------------------------------
# Suite header
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host ("=" * 62) -ForegroundColor Cyan
Write-Host "  Atieh Clinic API - Smoke Test Suite" -ForegroundColor Cyan
Write-Host "  Target : $BaseUrl" -ForegroundColor Cyan
Write-Host "  Time   : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
Write-Host ("=" * 62) -ForegroundColor Cyan
Write-Host ""

# ---------------------------------------------------------------------------
# TEST 1: /health
# ---------------------------------------------------------------------------

Invoke-Check `
    -Label "GET /health" `
    -Uri   "$BaseUrl/health" `
    -Assertions @(
        @{ Field = "status";    Expected = "ok";    Op = "eq"      },
        @{ Field = "version";   Expected = "1.0.0"; Op = "eq"      },
        @{ Field = "timestamp"; Expected = "";      Op = "notnull" }
    )

# ---------------------------------------------------------------------------
# TEST 2: /api/import/ping
# ---------------------------------------------------------------------------

Invoke-Check `
    -Label "GET /api/import/ping" `
    -Uri   "$BaseUrl/api/import/ping" `
    -Assertions @(
        @{ Field = "status"; Expected = "ok"; Op = "eq" }
    )

# ---------------------------------------------------------------------------
# TEST 3: /ai/patient-history-score/21
# ---------------------------------------------------------------------------

Invoke-Check `
    -Label "GET /ai/patient-history-score/21" `
    -Uri   "$BaseUrl/ai/patient-history-score/21" `
    -Assertions @(
        @{ Field = "patient_id";    Expected = 21;  Op = "eq" },
        @{ Field = "history_score"; Expected = 0;   Op = "gt" },
        @{ Field = "history_score"; Expected = 100; Op = "lt" }
    )

# ---------------------------------------------------------------------------
# TEST 4: /ai/top-patients?limit=5&smoke=1&days=7
#   smoke=1 caps scoring at 5 patients and skips the full sort,
#   so this test completes in ~2s instead of ~9s.
# ---------------------------------------------------------------------------

Invoke-Check `
    -Label "GET /ai/top-patients?limit=5&smoke=1&days=7" `
    -Uri   "$BaseUrl/ai/top-patients?limit=5&smoke=1&days=7" `
    -Assertions @(
        @{ Field = "limit";        Expected = 5;     Op = "eq"      },
        @{ Field = "smoke";        Expected = "True"; Op = "eq"      },
        @{ Field = "generated_at"; Expected = "";    Op = "notnull" }
    )

# Extra: items array count and shape
Write-Sep
Write-Host "  CHECK: top-patients items array shape" -ForegroundColor Cyan
try {
    $r     = Invoke-RestMethod -Uri "$BaseUrl/ai/top-patients?limit=5&smoke=1&days=7" -TimeoutSec $TimeoutSec
    $count = $r.items.Count

    if ($count -eq 5) {
        Mark-Pass -Label "items.Count eq 5" -Detail "actual=$count"
    } else {
        Mark-Fail -Label "items.Count eq 5" -Detail "actual=$count"
        Write-Host ""
        Write-Host "  Fail-fast triggered. Aborting." -ForegroundColor Red
        exit 1
    }

    # Validate each item: patient_id exists, score in [0,100]
    $shapeOk = $true
    foreach ($item in $r.items) {
        if ($null -eq $item.patient_id -or
            $null -eq $item.history_score -or
            $item.history_score -lt 0 -or
            $item.history_score -gt 100) {
            $shapeOk = $false
            Mark-Fail -Label "item shape" -Detail "bad item: $($item | ConvertTo-Json -Compress)"
            break
        }
    }
    if ($shapeOk) {
        Mark-Pass -Label "all items have valid patient_id + history_score in [0,100]" -Detail "$count items"
    }

    # Human-readable top-5 listing
    Write-Host ""
    Write-Host "  Top-5 ranked patients:" -ForegroundColor DarkCyan
    foreach ($item in $r.items) {
        Write-Host ("    patient_id={0,-8}  history_score={1}" -f $item.patient_id, $item.history_score) -ForegroundColor Gray
    }

} catch {
    Mark-Fail -Label "top-patients items check" -Detail $_.Exception.Message
    Write-Host ""
    Write-Host "  Fail-fast triggered. Aborting." -ForegroundColor Red
    exit 1
}

# ---------------------------------------------------------------------------
# TEST 5: GET /appointments?limit=5&future_only=false
#   future_only=false is required because the clinic DB contains historical
#   appointments; the default future_only=true would return 0 rows.
#   Validates:
#     - HTTP 200 (no ResponseValidationError from Optional enum fields)
#     - Paginated envelope present (total, items)
#     - items.Count == 5
#     - Each item has id (appointment id) and patient_id
# ---------------------------------------------------------------------------

Write-Sep
Write-Host "  TEST : GET /appointments?limit=5&future_only=false" -ForegroundColor Cyan
$apptUrl = "$BaseUrl/appointments?limit=5&future_only=false"
Write-Host "   GET  $apptUrl" -ForegroundColor DarkCyan

$t0 = Get-Date
try {
    $apptResp = Invoke-RestMethod -Uri $apptUrl -Method GET -TimeoutSec $TimeoutSec -ErrorAction Stop
    $ms = [int]((Get-Date) - $t0).TotalMilliseconds
    Write-Host "        HTTP 200  ${ms}ms" -ForegroundColor DarkGray
} catch {
    $ms   = [int]((Get-Date) - $t0).TotalMilliseconds
    $code = $_.Exception.Response.StatusCode.value__
    Mark-Fail -Label "GET /appointments HTTP 200" -Detail "HTTP $code after ${ms}ms  $($_.Exception.Message)"
    Write-Host ""
    Write-Host "  Fail-fast triggered. Aborting." -ForegroundColor Red
    exit 1
}

# Envelope fields
if ($null -ne $apptResp.total -and $apptResp.total -ge 0) {
    Mark-Pass -Label "response has total field" -Detail "total=$($apptResp.total)"
} else {
    Mark-Fail -Label "response has total field" -Detail "total=$($apptResp.total)"
}

# items count
$apptCount = if ($null -ne $apptResp.items) { $apptResp.items.Count } else { 0 }
if ($apptCount -eq 5) {
    Mark-Pass -Label "items.Count eq 5" -Detail "actual=$apptCount"
} else {
    Mark-Fail -Label "items.Count eq 5" -Detail "actual=$apptCount"
    Write-Host ""
    Write-Host "  Fail-fast triggered. Aborting." -ForegroundColor Red
    exit 1
}

# Each item must have id (appointment id) and patient_id
$shapeOk = $true
foreach ($item in $apptResp.items) {
    if ($null -eq $item.id -or $null -eq $item.patient_id) {
        $shapeOk = $false
        Mark-Fail -Label "item has id + patient_id" -Detail "bad item: $($item | ConvertTo-Json -Compress)"
        break
    }
}
if ($shapeOk) {
    Mark-Pass -Label "all items have id + patient_id" -Detail "$apptCount items validated"
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

$elapsed = [int]((Get-Date) - $t_suite).TotalMilliseconds

Write-Host ""
Write-Host ("=" * 62) -ForegroundColor Cyan
Write-Host "  RESULTS" -ForegroundColor Cyan
Write-Host ("=" * 62) -ForegroundColor Cyan
Write-Host ("  Passed : {0}" -f $passed) -ForegroundColor Green

$failColor = if ($failed -gt 0) { "Red" } else { "Green" }
Write-Host ("  Failed : {0}" -f $failed) -ForegroundColor $failColor
Write-Host ("  Total  : {0}  ({1}ms wall time)" -f ($passed + $failed), $elapsed) -ForegroundColor White
Write-Host ("=" * 62) -ForegroundColor Cyan
Write-Host ""

if ($failed -gt 0) {
    Write-Host "  SMOKE: FAILED" -ForegroundColor Red
    exit 1
} else {
    Write-Host "  SMOKE: PASSED" -ForegroundColor Green
    exit 0
}
