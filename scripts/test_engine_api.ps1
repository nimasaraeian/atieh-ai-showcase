# Run from repo root
Write-Host "=== ATIEH ENGINE API TEST ==="

# 1) ensure openapi reachable
Invoke-RestMethod "http://127.0.0.1:8001/openapi.json" -Method Get | Out-Null
"OpenAPI OK ✅"

# 2) ensure new endpoint exists in openapi (quick string check)
$openapi = Invoke-RestMethod "http://127.0.0.1:8001/openapi.json" -Method Get | ConvertTo-Json -Depth 8
if ($openapi -match "/ai/engine/recommend-slot") { "Route exists in OpenAPI ✅" } else { "Route NOT found in OpenAPI ❌" }

# 3) call new endpoint with JSON body
$body = @{
  service   = "کشیدن دندان"
  insurance = "ایران"
  backlog   = "درمان ریشه"
  doctor    = 1009
  weekday   = "پنجشنبه"
} | ConvertTo-Json -Depth 5

Invoke-RestMethod "http://127.0.0.1:8001/ai/engine/recommend-slot" `
  -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body $body |
  ConvertTo-Json -Depth 10

# 4) check output files
Get-Item .\data\outputs\slot_recommendations.csv, .\data\outputs\schedule_draft.csv |
  Select Name, Length, LastWriteTime
