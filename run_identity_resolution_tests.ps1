# ==========================================
# Atieh AI Identity Resolution Test Runner
# ==========================================

$PROJECT_PATH = "C:\Users\USER\Documents\GitHub\atieh"
$DB_PATH = "atieh_clinic_recovery81_test.db"

Set-Location $PROJECT_PATH
$env:ATIEH_DB_PATH = $DB_PATH

Write-Host ""
Write-Host "=========================================="
Write-Host "Atieh AI Identity Resolution Test Runner"
Write-Host "=========================================="
Write-Host ""

New-Item -ItemType Directory -Force -Path ".\logs\identity_resolution_tests" | Out-Null

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Command,
        [string]$LogFile
    )

    Write-Host ""
    Write-Host "------------------------------------------"
    Write-Host "Running: $Name"
    Write-Host "------------------------------------------"

    & $Command *>&1 | Tee-Object $LogFile
}

# ==========================================
# 1 Schema
# ==========================================
Run-Step `
"Create Identity Schema" `
{ sqlite3 ".\$env:ATIEH_DB_PATH" ".read .\sql\identity_resolution\001_identity_resolution_schema.sql" } `
".\logs\identity_resolution_tests\01_schema.log"

# ==========================================
# 2 Indexes
# ==========================================
Run-Step `
"Create Indexes" `
{ sqlite3 ".\$env:ATIEH_DB_PATH" ".read .\sql\identity_resolution\002_identity_resolution_indexes.sql" } `
".\logs\identity_resolution_tests\02_indexes.log"

# ==========================================
# 3 Import Appointments
# ==========================================
Run-Step `
"Import Appointments" `
{ python .\scripts\import_appointments_unified.py } `
".\logs\identity_resolution_tests\03_import_appointments.log"

# ==========================================
# 4 Normalize Identity Fields
# ==========================================
Run-Step `
"Normalize Identity Fields" `
{ python .\scripts\normalize_identity_fields.py } `
".\logs\identity_resolution_tests\04_normalize_identity.log"

# ==========================================
# 5 Build Candidate Matches
# ==========================================
Run-Step `
"Build Candidate Matches" `
{ python .\scripts\build_identity_candidate_matches.py } `
".\logs\identity_resolution_tests\05_candidate_matches.log"

# ==========================================
# 6 Build Match Scores
# ==========================================
Run-Step `
"Build Match Scores" `
{ python .\scripts\build_identity_match_scores.py } `
".\logs\identity_resolution_tests\06_match_scores.log"

# ==========================================
# 7 Stats Report
# ==========================================
Run-Step `
"Generate Stats Report" `
{ python .\scripts\identity_resolution_stats.py } `
".\logs\identity_resolution_tests\07_stats.log"

# ==========================================
# DATABASE QUICK STATS
# ==========================================

Write-Host ""
Write-Host "=========================================="
Write-Host "Database Summary"
Write-Host "=========================================="

sqlite3 ".\$env:ATIEH_DB_PATH" "
SELECT 'appointments_unified_staging', COUNT(*) FROM appointments_unified_staging
UNION ALL
SELECT 'identity_normalized_payments', COUNT(*) FROM identity_normalized_payments
UNION ALL
SELECT 'identity_normalized_appointments', COUNT(*) FROM identity_normalized_appointments
UNION ALL
SELECT 'patients_identity_normalized', COUNT(*) FROM patients_identity_normalized
UNION ALL
SELECT 'identity_candidate_matches', COUNT(*) FROM identity_candidate_matches;
"

Write-Host ""
Write-Host "=========================================="
Write-Host "Confidence Tier Distribution"
Write-Host "=========================================="

sqlite3 ".\$env:ATIEH_DB_PATH" "
SELECT confidence_tier, COUNT(*)
FROM identity_candidate_matches
GROUP BY confidence_tier
ORDER BY confidence_tier;
"

Write-Host ""
Write-Host "=========================================="
Write-Host "Candidate Rules"
Write-Host "=========================================="

sqlite3 ".\$env:ATIEH_DB_PATH" "
SELECT candidate_rule, COUNT(*)
FROM identity_candidate_matches
GROUP BY candidate_rule
ORDER BY COUNT(*) DESC;
"

Write-Host ""
Write-Host "=========================================="
Write-Host "Identity Resolution Test Completed"
Write-Host "=========================================="