@echo off
REM Запуск из cmd.exe — обёртка для mvp-check.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0mvp-check.ps1" %*
