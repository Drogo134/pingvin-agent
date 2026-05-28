$envFile = Join-Path (Split-Path $PSScriptRoot -Parent) '.env'
Get-Content $envFile -Encoding UTF8 | Where-Object { $_ -match '^[^#].*=' } | ForEach-Object {
    $p = $_ -split '=', 2
    if ($p.Count -eq 2) { Set-Item -Path "Env:$($p[0].Trim())" -Value $p[1].Trim() }
}

$py = Join-Path $env:USERPROFILE '.openclaw\workspace\scripts\sbis_api.py'
Write-Host '=== test_auth ===' -ForegroundColor Cyan
python $py test_auth
Write-Host '=== list_appeals ===' -ForegroundColor Cyan
python (Join-Path (Split-Path $PSScriptRoot -Parent) 'scripts\sbis_list_appeals.py') 2>&1
