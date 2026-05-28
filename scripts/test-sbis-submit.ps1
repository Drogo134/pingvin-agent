$envFile = Join-Path (Split-Path $PSScriptRoot -Parent) '.env'
Get-Content $envFile -Encoding UTF8 | Where-Object { $_ -match '^[^#].*=' } | ForEach-Object {
    $p = $_ -split '=', 2
    if ($p.Count -eq 2) { Set-Item -Path "Env:$($p[0].Trim())" -Value $p[1].Trim() }
}
$env:SBIS_DEPARTMENT_NAME = 'РПК ПИНГВИН, ООО'
$env:SBIS_DEPARTMENT_ID = '4'
$env:SBIS_RECIPIENT_MODE = 'auto'
$env:SBIS_AUTO_SUBMIT = 'true'
$py = Join-Path $env:USERPROFILE '.openclaw\workspace\scripts\sbis_api.py'
$json = '{"appeal_id":"d0ed9465-510e-4918-b87b-14eb1215d621","description":"Test submit after discover"}'
python $py submit_appeal $json
