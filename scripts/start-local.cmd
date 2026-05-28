@echo off
REM Запуск из cmd.exe (не PowerShell) — обёртка для start-local.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-local.ps1" %*
