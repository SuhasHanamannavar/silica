@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0checkmate-view.ps1" %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [CHECKMATE] Execution failed or access denied by Checkmate Zero-Trust Guard.
)
echo.
pause
