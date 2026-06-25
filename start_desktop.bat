@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"
echo [start_desktop] repo = %cd%

powershell -NoProfile -ExecutionPolicy Bypass -File "%cd%\start_desktop.ps1"
if errorlevel 1 (
  echo [start_desktop] FAILED (exit=%errorlevel%)
  pause
  exit /b %errorlevel%
)

endlocal
