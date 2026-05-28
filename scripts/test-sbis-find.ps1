$envFile = Join-Path (Split-Path $PSScriptRoot -Parent) '.env'
Get-Content $envFile -Encoding UTF8 | Where-Object { $_ -match '^[^#].*=' } | ForEach-Object {
    $p = $_ -split '=', 2
    if ($p.Count -eq 2) { Set-Item -Path "Env:$($p[0].Trim())" -Value $p[1].Trim() }
}
$py = Join-Path $env:USERPROFILE '.openclaw\workspace\scripts\sbis_api.py'
$jsonFile = Join-Path $env:TEMP 'sbis-find.json'
@'
{"appeal_id":"d0ed9465-510e-4918-b87b-14eb1215d621"}
'@ | Set-Content $jsonFile -Encoding UTF8
python $py find_appeal (Get-Content $jsonFile -Raw)
