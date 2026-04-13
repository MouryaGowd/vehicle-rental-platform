@echo off
cd /d "%~dp0"
echo ============================================
echo  VehicleRent - First-Time Setup
echo ============================================
echo.

:: ── Step 1: Verify Python ────────────────────────────────────────────────────
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo.
    echo  Please install Python 3.8 or higher from:
    echo    https://python.org/downloads
    echo.
    echo  IMPORTANT: During installation, tick the checkbox
    echo             "Add Python to PATH" before clicking Install.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [1/4] %PYVER% detected.

:: ── Step 2: Create virtual environment ──────────────────────────────────────
echo [2/4] Setting up virtual environment...
if exist venv\Scripts\python.exe (
    echo       Already exists - skipping.
) else (
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo       Created.
)

:: ── Step 3: Install dependencies inside venv ────────────────────────────────
echo [3/4] Installing Flask and dependencies...
venv\Scripts\python.exe -m pip install --quiet --upgrade pip
venv\Scripts\python.exe -m pip install --quiet -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Dependency installation failed.
    echo         Check your internet connection and try again.
    pause
    exit /b 1
)
echo       Done.

:: ── Step 4: Initialize database ─────────────────────────────────────────────
echo [4/4] Initializing database...
venv\Scripts\python.exe init_db.py
if %errorlevel% neq 0 (
    echo [ERROR] Database initialization failed.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Setup complete!
echo.
echo  Next step: double-click  run.bat
echo ============================================
pause
