function Invoke-AtiehEngineRecommend {
  param(
    [Parameter(Mandatory=$true)][string]$service,
    [string]$weekday,
    [string]$insurance,
    [string]$backlog,
    [Nullable[int]]$doctor
  )

  # 1) hashtable پایه
  $payload = @{
    service   = $service
    weekday   = $weekday
    insurance = $insurance
    backlog   = $backlog
    doctor    = $doctor
  }

  # 2) حذف کلیدهای خالی (بدون pipe!)
  $clean = @{}
  foreach ($k in $payload.Keys) {
    $v = $payload[$k]
    if ($null -ne $v -and "$v".Trim() -ne "") {
      $clean[$k] = $v
    }
  }

  $json = $clean | ConvertTo-Json -Depth 10

  if ([string]::IsNullOrWhiteSpace($json)) {
    throw "JSON body is empty (unexpected). Payload keys: $($clean.Keys -join ', ')"
  }

  Invoke-RestMethod -Method Post `
    -Uri "http://127.0.0.1:8001/ai/engine/recommend-slot" `
    -ContentType "application/json; charset=utf-8" `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($json))
}

# تست سریع
$res = Invoke-AtiehEngineRecommend -service "کشیدن دندان" -weekday "پنجشنبه"
$res.input
$res.counts
$res.run_id
Import-Csv "data\outputs\runs\$($res.run_id)\slot_recommendations.csv" | Measure-Object