@echo off
cd /d "%~dp0"

echo Stopping JW Marriott Hotel Assistant...

taskkill /F /IM streamlit.exe >nul 2>nul
if not errorlevel 1 (
    echo Stopped.
    pause
    exit /b 0
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$p = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*streamlit*app.py*' };" ^
    "if ($p) { $p | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }; Write-Host 'Stopped.' } else { Write-Host 'No running instance found.' }"

pause
