@echo off
cd /d "%~dp0"

if not exist venv (
    echo Virtual environment not found - running first-time setup...
    call setup.bat
    if errorlevel 1 exit /b 1
)

call venv\Scripts\activate.bat

if not exist chroma_db (
    echo Knowledge base not found - building it now...
    python ingest.py
    if errorlevel 1 (
        echo [ERROR] Failed to build the vector database.
        pause
        exit /b 1
    )
)

echo Starting JW Marriott Hotel Assistant...
echo A browser tab will open automatically. Close this window to stop the app.
streamlit run app.py
pause
