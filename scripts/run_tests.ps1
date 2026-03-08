$repoRoot   = Split-Path -Parent $PSScriptRoot
$outputFile = Join-Path $repoRoot "pytest_run.txt"

Push-Location $repoRoot

try {
    Write-Host "Running tests..."

    # Pipe stdout directly to Out-File.
    # - Out-File drains the pipe continuously, so no buffer overflow even with -s mode.
    # - Stderr (app/model log lines) goes to the console live – no NativeCommandError noise.
    # - $LASTEXITCODE is correctly set to pytest's exit code after the pipeline ends.
    python -m pytest tests/ --tb=short | Out-File -FilePath $outputFile -Encoding utf8
    $exitCode = $LASTEXITCODE

} finally {
    Pop-Location
}

Write-Host ""
Write-Host "===== Last 120 lines of pytest_run.txt ====="
Get-Content $outputFile -Tail 120

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "Tests PASSED (exit code 0)"
} else {
    Write-Host "Tests FAILED (exit code $exitCode)"
    exit $exitCode
}
