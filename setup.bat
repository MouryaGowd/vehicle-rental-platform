@echo off
echo ============================================
echo  VehicleRent — Setup
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo [1/3] Python found.

:: Install dependencies
echo [2/3] Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

:: Initialize database
echo [3/3] Setting up database...
python init_db.py
if %errorlevel% neq 0 (
    echo [ERROR] Database setup failed.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Setup complete!
echo  Run  run.bat  to start the server.
echo ============================================
pause
