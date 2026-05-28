$envFile = Join-Path (Split-Path $PSScriptRoot -Parent) '.env'
Get-Content $envFile -Encoding UTF8 | Where-Object { $_ -match '^[^#].*=' } | ForEach-Object {
    $p = $_ -split '=', 2
    if ($p.Count -eq 2) { Set-Item -Path "Env:$($p[0].Trim())" -Value $p[1].Trim() }
}
$py = Join-Path $env:USERPROFILE '.openclaw\workspace\scripts\notify_managers.py'
python $py "Test notify_managers.py - novyi lid: Vizitki 100 sht, ~3500 r. Klient: test_user"
