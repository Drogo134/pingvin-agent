# ================================================================
# РПК ПинГвин — Локальная настройка (Windows, без Docker)
# Запускать из корня проекта: .\scripts\setup-local.ps1
# ================================================================

$Root = Split-Path $PSScriptRoot -Parent
$WorkspaceDir = "$Root\workspace"
$OpenClawDir = "$env:USERPROFILE\.openclaw"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  OpenClaw AI Agent — Local Setup" -ForegroundColor Cyan
Write-Host "  РПК ПинГвин, Домодедово" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# --- Проверка Node.js ---
$nodeVer = node --version 2>$null
if (-not $nodeVer) {
    Write-Host "ОШИБКА: Node.js не найден. Скачать: https://nodejs.org (нужна версия 22+)" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Node.js: $nodeVer" -ForegroundColor Green

# --- Добавить npm global в PATH ---
$npmBin = "$env:APPDATA\npm"
if (-not ($env:PATH -split ';' | Where-Object { $_ -eq $npmBin })) {
    $env:PATH = "$npmBin;$env:PATH"
}

# --- Проверка/установка OpenClaw ---
$ocVer = openclaw --version 2>$null
if (-not $ocVer) {
    Write-Host "[..] Установка OpenClaw..." -ForegroundColor Yellow
    npm install -g openclaw@latest
    $ocVer = & "$npmBin\openclaw" --version 2>$null
}
Write-Host "[OK] OpenClaw: $ocVer" -ForegroundColor Green

# --- Проверка/установка pm2 ---
$pm2Ver = pm2 --version 2>$null
if (-not $pm2Ver) {
    Write-Host "[..] Установка pm2..." -ForegroundColor Yellow
    npm install -g pm2
}
Write-Host "[OK] pm2 готов" -ForegroundColor Green

# --- Создать .env ---
$envFile = "$Root\.env"
if (-not (Test-Path $envFile)) {
    Copy-Item "$Root\.env.example" $envFile
    Write-Host ""
    Write-Host "*** ВАЖНО: Заполните $envFile ***" -ForegroundColor Yellow
    Write-Host "Обязательные переменные:" -ForegroundColor Yellow
    Write-Host "  ANTHROPIC_API_KEY   — https://console.anthropic.com" -ForegroundColor White
    Write-Host "  TELEGRAM_BOT_TOKEN  — от @BotFather в Telegram" -ForegroundColor White
    Write-Host "  MANAGER_TELEGRAM_CHAT_IDS — chat_id менеджеров через запятую (@userinfobot)" -ForegroundColor White
    Write-Host ""
    Start-Process notepad $envFile
    Write-Host "Нажмите Enter после заполнения .env..." -ForegroundColor Cyan
    Read-Host
}

# --- Загрузить .env ---
Get-Content $envFile | Where-Object { $_ -match '^[^#].*=.+' } | ForEach-Object {
    $parts = $_ -split '=', 2
    [System.Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), 'Process')
}

# --- Синхронизировать workspace в .openclaw ---
Write-Host "[..] Синхронизация workspace..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $OpenClawDir | Out-Null
New-Item -ItemType Directory -Force -Path "$OpenClawDir\workspace\skills" | Out-Null

foreach ($file in @('AGENTS.md', 'SOUL.md', 'HEARTBEAT.md', 'IDENTITY.md', 'USER.md', 'TOOLS.md')) {
    $src = "$WorkspaceDir\$file"
    if (Test-Path $src) { Copy-Item $src "$OpenClawDir\workspace\$file" -Force }
}

# Синхронизировать skills и scripts
Get-ChildItem "$WorkspaceDir\skills" -Directory | ForEach-Object {
    $dest = "$OpenClawDir\workspace\skills\$($_.Name)"
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    Copy-Item "$($_.FullName)\*" $dest -Recurse -Force
}
if (Test-Path "$WorkspaceDir\scripts") {
    New-Item -ItemType Directory -Force -Path "$OpenClawDir\workspace\scripts" | Out-Null
    Copy-Item "$WorkspaceDir\scripts\*" "$OpenClawDir\workspace\scripts\" -Recurse -Force
}
Write-Host "[OK] Workspace синхронизирован" -ForegroundColor Green

# --- Создать openclaw.json (каталог моделей для выбора в UI) ---
$configTemplate = Get-Content "$Root\openclaw.json" -Raw
$tgToken = if ($env:TELEGRAM_BOT_TOKEN) { $env:TELEGRAM_BOT_TOKEN } else { '' }
$configTemplate = $configTemplate -replace '\$\{TELEGRAM_BOT_TOKEN\}', $tgToken
$gatewayToken = if ($env:OPENCLAW_GATEWAY_TOKEN) { $env:OPENCLAW_GATEWAY_TOKEN } else { 'pingvin-mvp-dashboard-2026' }
$configTemplate = $configTemplate -replace '\$\{OPENCLAW_GATEWAY_TOKEN\}', $gatewayToken

$configObj = $configTemplate | ConvertFrom-Json
$configObj.agents.defaults.workspace = "$OpenClawDir\workspace"
$configObj | ConvertTo-Json -Depth 12 | Out-File "$OpenClawDir\openclaw.json" -Encoding utf8
Write-Host "[OK] Каталог моделей (OpenAI + Anthropic) в agents.defaults.models" -ForegroundColor Green

# --- Валидация конфига ---
$env:PATH = "$npmBin;$env:PATH"
$validation = & "$npmBin\openclaw" config validate 2>&1
if ($validation -match "valid") {
    Write-Host "[OK] Config валиден" -ForegroundColor Green
} else {
    Write-Host "[WARN] Config: $validation" -ForegroundColor Yellow
}

# --- Проверка skills ---
$skillsOutput = & "$npmBin\openclaw" skills list 2>&1
$readyCount = ($skillsOutput | Select-String "sales-intake|pricing|crm-sbis|knowledge-base|handoff|followup|email-intake|file-check").Count
Write-Host "[OK] Skills агента обнаружено: $readyCount/8" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Setup завершён! Запуск: .\scripts\start-local.ps1" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
