@echo off
cd /d "%~dp0"

echo ==========================================
echo  JW Marriott Hotel Assistant - First-time setup
echo ==========================================

where python >nul 2>nul
if errorlevel 1 (
    echo "python" not found on PATH - trying to fix that automatically...
    call add_python_to_path.bat
    where python >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] Still could not find Python. Install Python 3.10+ from python.org
        echo         and make sure "Add python.exe to PATH" is checked during install,
        echo         then re-run this file.
        pause
        exit /b 1
    )
)

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo Installing dependencies (this can take a few minutes)...
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Dependency installation failed. See the messages above.
    pause
    exit /b 1
)

echo Building the hotel knowledge base...
python ingest.py
if errorlevel 1 (
    echo [ERROR] Failed to build the vector database.
    pause
    exit /b 1
)

echo.
echo Setup complete! Double-click run.bat to start the assistant.
pause
