# Pingvin RPK - local OpenClaw agent (Windows, pm2)
# Any run without -Stop/-Logs/-Status = full auto-deploy

param(
    [switch]$Stop,
    [switch]$Restart,
    [switch]$Logs,
    [switch]$Status,
    [switch]$Sync,
    [switch]$NoSmokeTest
)

$Root = Split-Path $PSScriptRoot -Parent
$npmBin = "$env:APPDATA\npm"
$NodeExe = 'C:\Program Files\nodejs\node.exe'
if (-not (Test-Path $NodeExe)) { $NodeExe = 'node' }
$env:PATH = "C:\Program Files\nodejs;$npmBin;$env:PATH"
$OpenClawDir = "$env:USERPROFILE\.openclaw"
$WorkspaceDir = "$Root\workspace"
$ConfigHashFile = "$OpenClawDir\.pingvin-config-hash"
$OpenClawMjs = "$npmBin\node_modules\openclaw\openclaw.mjs"

$envFile = "$Root\.env"
if (Test-Path $envFile) {
    Get-Content $envFile -Encoding UTF8 | Where-Object { $_ -match '^[^#].*=.+' } | ForEach-Object {
        $parts = $_ -split '=', 2
        if ($parts.Count -eq 2) {
            [System.Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), 'Process')
        }
    }
}

function Sync-OpenClawConfig {
    param([string]$Root, [string]$OpenClawDir)

    Write-Host "[1/6] Sync workspace + openclaw.json..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Force -Path "$OpenClawDir\workspace\skills" | Out-Null

    foreach ($file in @('AGENTS.md', 'SOUL.md', 'HEARTBEAT.md', 'IDENTITY.md', 'USER.md', 'TOOLS.md', 'VOICE.md')) {
        $src = "$WorkspaceDir\$file"
        if (Test-Path $src) { Copy-Item $src "$OpenClawDir\workspace\$file" -Force }
    }
    Get-ChildItem "$WorkspaceDir\skills" -Directory | ForEach-Object {
        $dest = "$OpenClawDir\workspace\skills\$($_.Name)"
        New-Item -ItemType Directory -Force -Path $dest | Out-Null
        Copy-Item "$($_.FullName)\*" $dest -Recurse -Force
    }
    if (Test-Path "$WorkspaceDir\scripts") {
        New-Item -ItemType Directory -Force -Path "$OpenClawDir\workspace\scripts" | Out-Null
        Copy-Item "$WorkspaceDir\scripts\*" "$OpenClawDir\workspace\scripts\" -Recurse -Force
    }

    $configTemplate = Get-Content "$Root\openclaw.json" -Raw -Encoding UTF8
    $tgToken = if ($env:TELEGRAM_BOT_TOKEN) { $env:TELEGRAM_BOT_TOKEN } else { '' }
    $configTemplate = $configTemplate -replace '\$\{TELEGRAM_BOT_TOKEN\}', $tgToken
    $gatewayToken = if ($env:OPENCLAW_GATEWAY_TOKEN) { $env:OPENCLAW_GATEWAY_TOKEN } else { 'pingvin-mvp-dashboard-2026' }
    $configTemplate = $configTemplate -replace '\$\{OPENCLAW_GATEWAY_TOKEN\}', $gatewayToken
    $wsPath = (($OpenClawDir -replace '\\', '/') + '/workspace')
    $configTemplate = $configTemplate -replace '"/app/workspace"', "`"$wsPath`""

    $ownerAllow = @()
    $idsRaw = if ($env:MANAGER_TELEGRAM_CHAT_IDS) { $env:MANAGER_TELEGRAM_CHAT_IDS } else { $env:MANAGER_TELEGRAM_CHAT_ID }
    if ($idsRaw) {
        $ownerAllow = ($idsRaw -split '[,;]') | ForEach-Object { $_.Trim() } | Where-Object { $_ } | ForEach-Object { "telegram:$_" }
    }
    $cfg = $configTemplate | ConvertFrom-Json
    if (-not $cfg.commands) { $cfg | Add-Member -NotePropertyName commands -NotePropertyValue ([pscustomobject]@{}) }
    $cfg.commands | Add-Member -NotePropertyName ownerAllowFrom -NotePropertyValue $ownerAllow -Force

    $cfgJsonPath = Join-Path $OpenClawDir 'openclaw.json.tmp'
    $cfgJsonText = $cfg | ConvertTo-Json -Depth 30
    [System.IO.File]::WriteAllText($cfgJsonPath, $cfgJsonText, [System.Text.UTF8Encoding]::new($false))
    $mergeScript = (Join-Path $Root 'scripts\merge-openclaw-config.cjs')
    node $mergeScript $cfgJsonPath 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: failed to merge manager direct config" -ForegroundColor Red
        exit 1
    }
    $configOut = Get-Content $cfgJsonPath -Raw -Encoding UTF8
    Remove-Item $cfgJsonPath -Force -ErrorAction SilentlyContinue

    attrib -R "$OpenClawDir\openclaw.json" 2>$null | Out-Null
    [System.IO.File]::WriteAllText(
        "$OpenClawDir\openclaw.json",
        $configOut,
        [System.Text.UTF8Encoding]::new($false)
    )
    $validate = & node $OpenClawMjs doctor 2>&1 | Out-String
    if ($validate -match 'config is invalid|Problem:') {
        Write-Host "ERROR: openclaw.json failed validation after sync" -ForegroundColor Red
        ($validate -split "`n" | Select-Object -First 12) | ForEach-Object { Write-Host "       $_" -ForegroundColor Gray }
        exit 1
    }
    Copy-Item "$OpenClawDir\openclaw.json" "$OpenClawDir\openclaw.json.last-good" -Force
    Set-OpenClawConfigReadOnly -OpenClawDir $OpenClawDir -ReadOnly $true
    Write-Host "       OK" -ForegroundColor Green
}

function Set-OpenClawConfigReadOnly {
    param([string]$OpenClawDir, [bool]$ReadOnly)

    $cfgPath = "$OpenClawDir\openclaw.json"
    if (-not (Test-Path $cfgPath)) { return }
    if ($ReadOnly) { attrib +R $cfgPath 2>$null | Out-Null }
    else { attrib -R $cfgPath 2>$null | Out-Null }
}
function Restore-OpenClawConfigIfStripped {
    param([string]$OpenClawDir)

    $configPath = "$OpenClawDir\openclaw.json"
    $lastGood = "$OpenClawDir\openclaw.json.last-good"
    if (-not (Test-Path $lastGood)) { return $false }

    try {
        $j = Get-Content $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $hasSkills = $j.agents.defaults.skills -and @($j.agents.defaults.skills).Count -ge 3
        $hasPlugins = $j.plugins -and $j.plugins.entries -and $j.plugins.entries.openai
        $hasCommands = $null -ne $j.commands
        $hasHistory = $null -ne $j.channels.telegram.dmHistoryLimit
        $hasTimeout = $null -ne $j.agents.defaults.timeoutSeconds
        $stripped = (-not $hasSkills) -or (-not $hasPlugins) -or (-not $hasCommands) -or (-not $hasHistory) -or (-not $hasTimeout)
        if ($stripped) {
            Write-Host "       Restoring openclaw.json from last-good (gateway/dashboard stripped it)" -ForegroundColor Yellow
            Set-OpenClawConfigReadOnly -OpenClawDir $OpenClawDir -ReadOnly $false
            Copy-Item $lastGood $configPath -Force
            Set-OpenClawConfigReadOnly -OpenClawDir $OpenClawDir -ReadOnly $true
            return $true
        }
    } catch {}
    return $false
}

function Ensure-OpenClawConfigLive {
    param([string]$OpenClawDir, [string]$Root)

    if (-not (Restore-OpenClawConfigIfStripped -OpenClawDir $OpenClawDir)) { return }

    Write-Host "       Restarting gateway after config restore..." -ForegroundColor Yellow
    Restart-PingvinAgent -Root $Root
    Wait-GatewayReady -TimeoutSec 60 | Out-Null
}

function Test-OpenClawConfig {
    param([string]$OpenClawDir)

    $configJson = ($OpenClawDir -replace '\\', '/') + '/openclaw.json'
    $check = @"
try {
  const j = require('$configJson');
  const ws = j.agents?.defaults?.workspace || '';
  const rt = j.agents?.defaults?.models?.['openai/gpt-4o']?.agentRuntime?.id;
  const fb = j.agents?.defaults?.model?.fallbacks;
  const to = j.agents?.defaults?.timeoutSeconds || 0;
  const openaiPlugin = j.plugins?.entries?.openai?.enabled;
  if (!ws.includes('/')) throw new Error('workspace path must use forward slashes');
  if (rt !== 'pi') throw new Error('openai/gpt-4o must use agentRuntime pi, got ' + rt);
  if (Array.isArray(fb) && fb.length > 0 && !(fb.length === 1 && fb[0] === 'openai/gpt-4o-mini')) throw new Error('fallbacks must be empty or only openai/gpt-4o-mini');
  if (to < 120) throw new Error('agents.defaults.timeoutSeconds should be >= 120');
  if (openaiPlugin === true) throw new Error('plugins.entries.openai must be disabled');
  const tgTo = j.channels?.telegram?.timeoutSeconds;
  if (typeof tgTo === 'number' && tgTo > 50) throw new Error('channels.telegram.timeoutSeconds must be <= 50 (Telegram long-poll limit)');
  console.log('VALID');
} catch (e) {
  console.error('INVALID: ' + e.message);
  process.exit(1);
}
"@
    $out = node -e $check 2>&1
    return ($LASTEXITCODE -eq 0 -and ($out -match 'VALID'))
}

function Ensure-OpenClawAuth {
    param([string]$OpenClawDir, [string]$OpenAiKey)

    Write-Host "[2/6] OpenAI auth-profiles..." -ForegroundColor Yellow
    if (-not $OpenAiKey -or $OpenAiKey -like '*YOUR*' -or $OpenAiKey -like '*HERE*') {
        Write-Host "       SKIP (OPENAI_API_KEY missing in .env)" -ForegroundColor Red
        return $false
    }

    $agentDir = "$OpenClawDir\agents\main\agent"
    New-Item -ItemType Directory -Force -Path $agentDir | Out-Null

    $authFile = "$agentDir\auth-profiles.json"
    $authObj = @{
        version  = 1
        profiles = @{
            'openai:default' = @{
                type     = 'api_key'
                provider = 'openai'
                key      = $OpenAiKey
            }
        }
        order = @{
            openai = @('openai:default')
        }
    }
    $authJson = $authObj | ConvertTo-Json -Depth 5
    [System.IO.File]::WriteAllText($authFile, $authJson, [System.Text.UTF8Encoding]::new($false))
    Write-Host "       OK" -ForegroundColor Green
    return $true
}

function Reset-StaleSessions {
    param([string]$OpenClawDir, [switch]$Force)

    Write-Host "[3/6] Session check..." -ForegroundColor Yellow
    $sessionsDir = "$OpenClawDir\agents\main\sessions"
    $storeFile = "$sessionsDir\sessions.json"
    New-Item -ItemType Directory -Force -Path $sessionsDir | Out-Null

    $configPath = "$OpenClawDir\openclaw.json"
    $newHash = (Get-FileHash $configPath -Algorithm SHA256).Hash
    $oldHash = if (Test-Path $ConfigHashFile) { (Get-Content $ConfigHashFile -Raw).Trim() } else { '' }
    $configChanged = ($newHash -ne $oldHash)

    $needsReset = $Force -or $configChanged
    if (-not $needsReset -and (Test-Path $storeFile)) {
        try {
            $raw = Get-Content $storeFile -Raw -Encoding UTF8
            if ($raw -and $raw.Trim() -ne '{}') {
                $store = $raw | ConvertFrom-Json
                $store.PSObject.Properties | ForEach-Object {
                    if ($_.Value.status -eq 'failed') { $needsReset = $true }
                    if ($_.Value.agentHarnessId -and $_.Value.agentHarnessId -ne 'pi') { $needsReset = $true }
                }
            }
        } catch { $needsReset = $true }
    }

    if ($needsReset) {
        Remove-Item "$sessionsDir\*.jsonl*" -Force -ErrorAction SilentlyContinue
        Remove-Item "$sessionsDir\*.telegram-messages.json" -Force -ErrorAction SilentlyContinue
        Remove-Item $storeFile -Force -ErrorAction SilentlyContinue
        $reason = if ($configChanged) { 'config updated' } else { 'stale/failed sessions' }
        Write-Host "       Reset ($reason), no /new needed" -ForegroundColor Green
    } else {
        Write-Host "       OK (sessions current)" -ForegroundColor Green
    }

    [System.IO.File]::WriteAllText($ConfigHashFile, $newHash, [System.Text.UTF8Encoding]::new($false))
}

function Invoke-OpenClawDoctorFix {
    Write-Host "[3b] openclaw doctor --fix..." -ForegroundColor Yellow
    node $OpenClawMjs doctor --fix 2>&1 | Out-Null
    Write-Host "       OK" -ForegroundColor Green
}

function Get-Pm2EnvBlock {
    param([hashtable]$Raw)
    $out = [ordered]@{}
    foreach ($key in $Raw.Keys) {
        $val = $Raw[$key]
        if ($null -eq $val) { continue }
        $s = "$val".Trim()
        if ($s -eq '' -or $s -ieq 'null') { continue }
        $out[$key] = $val
    }
    return $out
}

function Write-Pm2Config {
    param([string]$Root)

    $app = [ordered]@{
        name          = 'pingvin-agent'
        script        = $OpenClawMjs
        interpreter   = $NodeExe
        args          = @('gateway', '--port', '18789')
        cwd           = $Root
        watch         = $false
        restart_delay = 5000
        max_restarts  = 10
        env           = (Get-Pm2EnvBlock @{
                    OPENAI_API_KEY              = $env:OPENAI_API_KEY
                    TELEGRAM_BOT_TOKEN          = $env:TELEGRAM_BOT_TOKEN
                    TELEGRAM_BOT_USERNAME       = $env:TELEGRAM_BOT_USERNAME
                    OPENCLAW_GATEWAY_TOKEN      = $(if ($env:OPENCLAW_GATEWAY_TOKEN) { $env:OPENCLAW_GATEWAY_TOKEN } else { 'pingvin-mvp-dashboard-2026' })
                    MANAGER_TELEGRAM_CHAT_IDS   = $env:MANAGER_TELEGRAM_CHAT_IDS
                    MANAGER_TELEGRAM_CHAT_ID    = $env:MANAGER_TELEGRAM_CHAT_ID
                    SBIS_AUTH_URL               = $env:SBIS_AUTH_URL
                    SBIS_API_URL                = $env:SBIS_API_URL
                    SBIS_SUPPORT_URL            = $env:SBIS_SUPPORT_URL
                    SBIS_APPEAL_REGULATION_NAME = $env:SBIS_APPEAL_REGULATION_NAME
                    SBIS_LOGIN                  = $env:SBIS_LOGIN
                    SBIS_PASSWORD               = $env:SBIS_PASSWORD
                    SBIS_ACCOUNT_NUMBER         = $env:SBIS_ACCOUNT_NUMBER
                    SBIS_MANAGER_ID             = $env:SBIS_MANAGER_ID
                    SBIS_DEPARTMENT_ID          = $env:SBIS_DEPARTMENT_ID
                    SBIS_DEPARTMENT_NAME        = $env:SBIS_DEPARTMENT_NAME
                    SBIS_RECIPIENT_MODE         = $(if ($env:SBIS_RECIPIENT_MODE) { $env:SBIS_RECIPIENT_MODE } else { 'auto' })
                    SBIS_AUTO_SUBMIT            = $(if ($env:SBIS_AUTO_SUBMIT) { $env:SBIS_AUTO_SUBMIT } else { 'true' })
                    SBIS_ORG_INN                = $env:SBIS_ORG_INN
                    SBIS_ORG_KPP                = $env:SBIS_ORG_KPP
                    EMAIL_USER                  = $env:EMAIL_USER
                    EMAIL_PASSWORD              = $env:EMAIL_PASSWORD
                    EMAIL_IMAP                  = $env:EMAIL_IMAP
                    EMAIL_IMAP_HOST             = $env:EMAIL_IMAP_HOST
                    EMAIL_IMAP_PORT             = $env:EMAIL_IMAP_PORT
                    EMAIL_IMAP_USER             = $env:EMAIL_IMAP_USER
                    EMAIL_IMAP_PASSWORD         = $env:EMAIL_IMAP_PASSWORD
                    EMAIL_SMTP_HOST             = $env:EMAIL_SMTP_HOST
                    EMAIL_SMTP_PORT             = $env:EMAIL_SMTP_PORT
                    COMPANY_EMAIL               = $env:COMPANY_EMAIL
                    COMPANY_NAME                = $env:COMPANY_NAME
                    BUSINESS_HOURS_START        = $(if ($env:BUSINESS_HOURS_START) { $env:BUSINESS_HOURS_START } else { '9' })
                    BUSINESS_HOURS_END          = $(if ($env:BUSINESS_HOURS_END) { $env:BUSINESS_HOURS_END } else { '18' })
                    BUSINESS_TIMEZONE           = $(if ($env:BUSINESS_TIMEZONE) { $env:BUSINESS_TIMEZONE } else { 'Europe/Moscow' })
                    HTTP_PROXY                  = $env:HTTP_PROXY
                    HTTPS_PROXY                 = $env:HTTPS_PROXY
                })
    }
    if ($env:HTTPS_PROXY -or $env:HTTP_PROXY) {
        $bootstrap = ($Root + '\scripts\openclaw-proxy-bootstrap.cjs') -replace '\\', '/'
        $app.node_args = "--require $bootstrap"
        $px = if ($env:HTTPS_PROXY) { $env:HTTPS_PROXY } else { $env:HTTP_PROXY }
        Write-Host "       (proxy: $px)" -ForegroundColor Gray
    }
    $pm2Config = @{ apps = @($app) } | ConvertTo-Json -Depth 5

    $pm2ConfigFile = "$Root\pm2.config.json"
    [System.IO.File]::WriteAllText($pm2ConfigFile, $pm2Config, [System.Text.UTF8Encoding]::new($false))
    return $pm2ConfigFile
}

function Restart-PingvinAgent {
    param([string]$Root)

    Write-Host "[4/6] Hard restart gateway (pm2)..." -ForegroundColor Yellow
    Set-OpenClawConfigReadOnly -OpenClawDir $OpenClawDir -ReadOnly $true
    $pm2File = Write-Pm2Config -Root $Root

    pm2 stop pingvin-agent 2>$null | Out-Null
    pm2 delete pingvin-agent 2>$null | Out-Null
    Start-Sleep -Seconds 2
    pm2 start $pm2File 2>$null | Out-Null
    pm2 save 2>$null | Out-Null
    Write-Host "       OK (fresh process)" -ForegroundColor Green
}

function Warmup-GatewayAgent {
    Write-Host "[5b] Gateway warmup (first model turn)..." -ForegroundColor Yellow
    $token = if ($env:OPENCLAW_GATEWAY_TOKEN) { $env:OPENCLAW_GATEWAY_TOKEN } else { 'pingvin-mvp-dashboard-2026' }
    $env:OPENCLAW_GATEWAY_TOKEN = $token
    $out = & node $OpenClawMjs agent --agent main --message "ping" --timeout 180 2>&1 | Out-String
    if ($out -match 'codex.*not registered|All models failed|Something went wrong|403 Country') {
        Write-Host "       WARN (warmup failed, first TG message may be slow)" -ForegroundColor Yellow
        ($out -split "`n" | Select-Object -Last 5) | ForEach-Object { Write-Host "       $_" -ForegroundColor Gray }
        return $false
    }
    Write-Host "       OK" -ForegroundColor Green
    return $true
}

function Wait-GatewayReady {
    param([int]$TimeoutSec = 90)

    Write-Host "[5/6] Wait for gateway..." -ForegroundColor Yellow
    $token = if ($env:OPENCLAW_GATEWAY_TOKEN) { $env:OPENCLAW_GATEWAY_TOKEN } else { 'pingvin-mvp-dashboard-2026' }
    $deadline = (Get-Date).AddSeconds($TimeoutSec)

    while ((Get-Date) -lt $deadline) {
        try {
            $r = Invoke-RestMethod -Uri "http://127.0.0.1:18789/health" -Headers @{ Authorization = "Bearer $token" } -TimeoutSec 3
            if ($r.ok -or $r.status -eq 'ok' -or $r.healthy) {
                Write-Host "       OK (gateway online)" -ForegroundColor Green
                return $true
            }
        } catch {
            try {
                $tcp = Test-NetConnection -ComputerName 127.0.0.1 -Port 18789 -WarningAction SilentlyContinue
                if ($tcp.TcpTestSucceeded) {
                    Write-Host "       OK (port 18789)" -ForegroundColor Green
                    return $true
                }
            } catch {}
        }
        Start-Sleep -Seconds 2
    }
    Write-Host "       WARN (gateway timeout ${TimeoutSec}s)" -ForegroundColor Yellow
    return $false
}

function Test-AgentSmoke {
    Write-Host "[6/6] Smoke-test GPT-4o..." -ForegroundColor Yellow
    $out = & node $OpenClawMjs agent --agent main --message "Say exactly: PONG" --local 2>&1 | Out-String
    if ($out -notmatch 'codex.*not registered' -and $out -notmatch 'All models failed' -and ($out -match 'PONG' -or $out -match 'stopReason')) {
        Write-Host "       OK (model responds)" -ForegroundColor Green
        return $true
    }
    Write-Host "       FAIL" -ForegroundColor Red
    Write-Host ($out -split "`n" | Select-Object -Last 8 | Out-String) -ForegroundColor Gray
    return $false
}

function Invoke-FullDeploy {
    param([string]$Root, [switch]$SkipSmoke)

    Write-Host ""
    Write-Host "=== Pingvin auto-deploy ===" -ForegroundColor Cyan
    Write-Host ""

    $required = @('OPENAI_API_KEY', 'TELEGRAM_BOT_TOKEN')
    $missing = $required | Where-Object {
        $v = [System.Environment]::GetEnvironmentVariable($_, 'Process')
        -not $v -or $v -like '*YOUR*' -or $v -like '*HERE*'
    }
    if ($missing) {
        Write-Host "ERROR: missing in .env:" -ForegroundColor Red
        $missing | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
        exit 1
    }

    $sbisRecipient = $env:SBIS_DEPARTMENT_NAME, $env:SBIS_DEPARTMENT_ID, $env:SBIS_MANAGER_ID | Where-Object { $_ -and $_.Trim() }
    if (-not $sbisRecipient) {
        Write-Host "WARN: SBIS recipient not set (SBIS_DEPARTMENT_NAME / SBIS_MANAGER_ID)" -ForegroundColor Red
        Write-Host "       Appeals stay DRAFT - invisible in Contact Center until configured." -ForegroundColor Yellow
        Write-Host "       See scripts/sbis-recipients.md" -ForegroundColor Gray
    }

    # Stop gateway before writing openclaw.json
    pm2 stop pingvin-agent 2>$null | Out-Null
    Start-Sleep -Seconds 2
    Set-OpenClawConfigReadOnly -OpenClawDir $OpenClawDir -ReadOnly $false

    Sync-OpenClawConfig -Root $Root -OpenClawDir $OpenClawDir
    $null = Restore-OpenClawConfigIfStripped -OpenClawDir $OpenClawDir

    $tgSpool = "$OpenClawDir\telegram\ingress-spool-default"
    if (Test-Path $tgSpool) { Remove-Item $tgSpool -Recurse -Force -ErrorAction SilentlyContinue }

    if (-not (Test-OpenClawConfig -OpenClawDir $OpenClawDir)) {
        Write-Host "ERROR: invalid openclaw.json after sync" -ForegroundColor Red
        exit 1
    }
    Ensure-OpenClawAuth -OpenClawDir $OpenClawDir -OpenAiKey $env:OPENAI_API_KEY | Out-Null
    Reset-StaleSessions -OpenClawDir $OpenClawDir -Force
    Restart-PingvinAgent -Root $Root
    if (Wait-GatewayReady) {
        Warmup-GatewayAgent | Out-Null
    }

    if (-not $SkipSmoke) {
        $ok = Test-AgentSmoke
        if (-not $ok) { exit 1 }
    }
    Ensure-OpenClawConfigLive -OpenClawDir $OpenClawDir -Root $Root
    Set-OpenClawConfigReadOnly -OpenClawDir $OpenClawDir -ReadOnly $true

    $gt = if ($env:OPENCLAW_GATEWAY_TOKEN) { $env:OPENCLAW_GATEWAY_TOKEN } else { 'pingvin-mvp-dashboard-2026' }
    Write-Host ""
    Write-Host "Done. Telegram bot ready - just write a message." -ForegroundColor Green
    Write-Host "  Dashboard: http://127.0.0.1:18789/?token=$gt" -ForegroundColor Gray
    Write-Host ""
}

if ($Stop) {
    pm2 stop pingvin-agent 2>$null
    pm2 delete pingvin-agent 2>$null
    Write-Host "Agent stopped." -ForegroundColor Green
    exit 0
}

if ($Logs) {
    pm2 logs pingvin-agent
    exit 0
}

if ($Status) {
    pm2 status
    & "$npmBin\openclaw" doctor 2>&1
    if (Test-OpenClawConfig -OpenClawDir $OpenClawDir) {
        Write-Host "openclaw.json: VALID (pi runtime)" -ForegroundColor Green
    } else {
        Write-Host "openclaw.json: INVALID" -ForegroundColor Red
    }
    exit 0
}

Invoke-FullDeploy -Root $Root -SkipSmoke:$NoSmokeTest
