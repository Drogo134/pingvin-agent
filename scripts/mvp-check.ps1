# MVP automated checks — РПК ПинГвин
# Usage: .\scripts\mvp-check.ps1

$Root = Split-Path $PSScriptRoot -Parent
$npmBin = "$env:APPDATA\npm"
$env:PATH = "$npmBin;$env:PATH"
$envFile = "$Root\.env"
if (Test-Path $envFile) {
    Get-Content $envFile -Encoding UTF8 | Where-Object { $_ -match '^[^#].*=.+' } | ForEach-Object {
        $parts = $_ -split '=', 2
        if ($parts.Count -eq 2) {
            [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), 'Process')
        }
    }
}

$script:pass = 0
$script:fail = 0

function Test-Check($Name, $Ok, $Detail) {
    if ($Ok) { $script:pass++ } else { $script:fail++ }
    $icon = if ($Ok) { '[PASS]' } else { '[FAIL]' }
    Write-Host "$icon $Name" -ForegroundColor $(if ($Ok) { 'Green' } else { 'Red' })
    if ($Detail) { Write-Host "       $Detail" -ForegroundColor Gray }
}

Write-Host ""
Write-Host "=== MVP CHECK ===" -ForegroundColor Cyan
Write-Host ""

# OpenAI (direct — without proxy; gateway needs VPN/proxy if this fails with 403)
try {
    $h = @{ Authorization = "Bearer $env:OPENAI_API_KEY" }
    $code = curl.exe -s -o NUL -w '%{http_code}' -H "Authorization: Bearer $($env:OPENAI_API_KEY)" 'https://api.openai.com/v1/models'
    if ($code -eq '200') {
        Test-Check 'OpenAI API (gpt-4o)' $true 'HTTP 200'
    } elseif ($code -eq '403') {
        Test-Check 'OpenAI API (gpt-4o)' $false 'HTTP 403 region blocked — enable VPN and set HTTPS_PROXY in .env, then scripts\start-local.cmd'
    } else {
        Test-Check 'OpenAI API (gpt-4o)' $false "HTTP $code"
    }
} catch {
    Test-Check 'OpenAI API (gpt-4o)' $false $_.Exception.Message
}

# Telegram bot
try {
    $r = Invoke-RestMethod -Uri "https://api.telegram.org/bot$($env:TELEGRAM_BOT_TOKEN)/getMe" -TimeoutSec 15
    Test-Check 'Telegram bot' $r.ok "@$($r.result.username)"
} catch {
    Test-Check 'Telegram bot' $false $_.Exception.Message
}

# Saby auth
try {
    $out = python "$Root\scripts\sbis_test_auth.py" 2>$null
    $j = $out | ConvertFrom-Json
    Test-Check 'Saby auth' $j.ok "session $($j.session_prefix)..."
} catch {
    Test-Check 'Saby auth' $false $_.Exception.Message
}

# pricing
try {
    $p = Get-Content "$Root\workspace\skills\pricing\pricing-config.json" -Raw | ConvertFrom-Json
    Test-Check 'pricing-config.json' ($null -ne $p.signs) $p._meta.company
} catch {
    Test-Check 'pricing-config.json' $false $_.Exception.Message
}

# sync
$synced = "$env:USERPROFILE\.openclaw\workspace\scripts\sbis_api.py"
Test-Check 'Workspace synced' (Test-Path $synced) $synced

# openclaw.json valid + pi runtime
try {
    $cfgPath = ($env:USERPROFILE -replace '\\','/') + '/.openclaw/openclaw.json'
    $valid = node -e "const j=require('$cfgPath'); const rt=j.agents.defaults.models['openai/gpt-4o'].agentRuntime.id; if(rt!=='pi'||!j.agents.defaults.workspace.includes('/')) process.exit(1); console.log('pi');" 2>$null
    Test-Check 'openclaw.json (pi + valid path)' ($LASTEXITCODE -eq 0) 'openai/gpt-4o via API'
} catch {
    Test-Check 'openclaw.json (pi + valid path)' $false $_.Exception.Message
}

# skills
$skills = (Get-ChildItem "$Root\workspace\skills\*\SKILL.md").Count
Test-Check 'Skills (9+)' ($skills -ge 9) "$skills skills"

# pm2
try {
    $desc = & pm2 describe pingvin-agent 2>$null | Out-String
    $running = ($desc -match 'pingvin-agent') -and ($desc -match '\bonline\b')
    Test-Check 'PM2 agent online' $running $(if ($running) { 'online' } else { 'not running' })
} catch {
    Test-Check 'PM2 agent online' $false $_.Exception.Message
}

# Gateway
try {
    $token = if ($env:OPENCLAW_GATEWAY_TOKEN) { $env:OPENCLAW_GATEWAY_TOKEN } else { 'pingvin-mvp-dashboard-2026' }
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:18789/?token=$token" -TimeoutSec 8 -UseBasicParsing
    Test-Check 'Gateway UI :18789' ($r.StatusCode -eq 200) "HTTP $($r.StatusCode)"
} catch {
    Test-Check 'Gateway UI :18789' $false $_.Exception.Message
}

Write-Host ""
Write-Host "=== Result: $script:pass passed, $script:fail failed ===" -ForegroundColor $(if ($script:fail -eq 0) { 'Green' } else { 'Yellow' })
Write-Host ""
