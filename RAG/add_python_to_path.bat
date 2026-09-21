@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ==========================================
echo  Add Python to your Windows PATH
echo ==========================================

where python >nul 2>nul
if not errorlevel 1 (
    echo Python is already on PATH:
    where python
    echo Nothing to do.
    pause
    exit /b 0
)

echo "python" was not found on PATH. Searching common install locations...

set "FOUND="

for /d %%D in ("%LocalAppData%\Programs\Python\Python3*") do (
    if exist "%%D\python.exe" set "FOUND=%%D"
)

if not defined FOUND (
    for /d %%D in ("C:\Python3*") do (
        if exist "%%D\python.exe" set "FOUND=%%D"
    )
)

if not defined FOUND (
    for /d %%D in ("C:\Program Files\Python3*") do (
        if exist "%%D\python.exe" set "FOUND=%%D"
    )
)

if not defined FOUND (
    for /d %%D in ("C:\Program Files (x86)\Python3*") do (
        if exist "%%D\python.exe" set "FOUND=%%D"
    )
)

if not defined FOUND (
    echo [ERROR] Could not find a Python install automatically.
    echo         Install Python 3.10+ from https://www.python.org/downloads/
    echo         during setup, check "Add python.exe to PATH", then re-run this file.
    pause
    exit /b 1
)

echo Found Python at: %FOUND%
echo Adding it (and its Scripts folder) to your user PATH...

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$dirs = @('%FOUND%', '%FOUND%\Scripts');" ^
    "$current = [Environment]::GetEnvironmentVariable('Path', 'User');" ^
    "$parts = @(); if ($current) { $parts = $current.Split(';') | Where-Object { $_ -ne '' } };" ^
    "foreach ($d in $dirs) { if ($parts -notcontains $d) { $parts += $d } };" ^
    "$new = [string]::Join(';', $parts);" ^
    "[Environment]::SetEnvironmentVariable('Path', $new, 'User');" ^
    "Write-Host 'Updated user PATH.'"

if errorlevel 1 (
    echo [ERROR] Failed to update PATH. Try running this file as Administrator.
    pause
    exit /b 1
)

set "PATH=%FOUND%;%FOUND%\Scripts;%PATH%"

echo.
echo Done. Python is now on PATH for future terminals and double-clicked .bat files.
echo (Existing open windows will not see the change until reopened.)
python --version
pause
