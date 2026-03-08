$ErrorActionPreference = "Stop"

Set-Location "C:\Users\USER\Documents\GitHub\atieh"

$DbPath = ".\atieh_clinic_working.db"
$ExportDir = ".\exports"

New-Item -ItemType Directory -Force -Path $ExportDir | Out-Null

Write-Host "=== Exporting final operational outputs ==="

sqlite3 -header -csv $DbPath "
SELECT
    record_no,
    patient_name_canonical,
    mobile_canonical,
    financial_tier,
    action_type,
    action_priority_score,
    last_payment_date_raw,
    lifetime_net_received,
    followup_recommendation
FROM v_financial_followup_queue_contactable
ORDER BY action_priority_score DESC, lifetime_net_received DESC;
" > "$ExportDir\followup_queue_contactable.csv"

sqlite3 -header -csv $DbPath "
SELECT
    record_no,
    patient_name_canonical,
    mobile_canonical,
    financial_tier,
    action_type,
    action_priority_score,
    last_payment_date_raw,
    lifetime_net_received,
    followup_recommendation
FROM v_financial_followup_daily_balanced
ORDER BY action_priority_score DESC, lifetime_net_received DESC;
" > "$ExportDir\followup_daily_balanced.csv"

sqlite3 -header -csv $DbPath "
SELECT
    record_no,
    patient_name_canonical,
    mobile_canonical,
    financial_tier,
    action_type,
    scheduling_priority_score,
    scheduling_band,
    last_payment_date_raw,
    lifetime_net_received
FROM v_financial_scheduling_queue_top300
ORDER BY scheduling_priority_score DESC, lifetime_net_received DESC;
" > "$ExportDir\scheduling_queue_top300.csv"

Write-Host ""
Write-Host "=== QC Checks ==="

$followupCount = sqlite3 $DbPath "SELECT COUNT(*) FROM v_financial_followup_queue_contactable;"
$dailyCount = sqlite3 $DbPath "SELECT COUNT(*) FROM v_financial_followup_daily_balanced;"
$schedulingCount = sqlite3 $DbPath "SELECT COUNT(*) FROM v_financial_scheduling_queue_top300;"

$missingMobileScheduling = sqlite3 $DbPath "
SELECT COUNT(*)
FROM v_financial_scheduling_queue_top300
WHERE mobile_canonical IS NULL
   OR TRIM(mobile_canonical) = '';
"

$duplicateRecordNoScheduling = sqlite3 $DbPath "
SELECT COUNT(*)
FROM (
    SELECT record_no
    FROM v_financial_scheduling_queue_top300
    GROUP BY record_no
    HAVING COUNT(*) > 1
);
"

$duplicateMobileDaily = sqlite3 $DbPath "
SELECT COUNT(*)
FROM (
    SELECT mobile_canonical
    FROM v_financial_followup_daily_balanced
    GROUP BY mobile_canonical
    HAVING COUNT(*) > 1
);
"

Write-Host "followup_queue_contactable rows: $followupCount"
Write-Host "followup_daily_balanced rows:   $dailyCount"
Write-Host "scheduling_queue_top300 rows:   $schedulingCount"
Write-Host "missing mobile in scheduling:   $missingMobileScheduling"
Write-Host "duplicate record_no scheduling: $duplicateRecordNoScheduling"
Write-Host "duplicate mobile daily:         $duplicateMobileDaily"

Write-Host ""
Write-Host "=== Output files ==="
Get-ChildItem $ExportDir | Select-Object Name, Length, LastWriteTime

Write-Host ""
Write-Host "Final operational export completed."