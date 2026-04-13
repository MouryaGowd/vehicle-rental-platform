@echo off
cd /d "%~dp0"
echo ============================================
echo  VehicleRent - Starting Server
echo ============================================
echo.

:: ── Check virtual environment ────────────────────────────────────────────────
if not exist venv\Scripts\python.exe (
    echo [ERROR] Virtual environment not found.
    echo         Please run setup.bat first.
    pause
    exit /b 1
)

:: ── Initialize DB if missing ─────────────────────────────────────────────────
if not exist rental.db (
    echo [INFO] Database not found. Initializing...
    venv\Scripts\python.exe init_db.py
    echo.
)

echo  Server starting at:
echo.
echo    http://localhost:5000
echo.
echo  Press Ctrl+C to stop.
echo ============================================
echo.

venv\Scripts\python.exe app.py

pause
