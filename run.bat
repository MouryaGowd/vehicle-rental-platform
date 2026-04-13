@echo off
echo ============================================
echo  VehicleRent — Starting Server
echo ============================================
echo.

:: Check if database exists
if not exist rental.db (
    echo [WARNING] Database not found. Running setup first...
    python init_db.py
    echo.
)

echo Server starting at http://localhost:5000
echo Press Ctrl+C to stop.
echo.

python app.py

pause
