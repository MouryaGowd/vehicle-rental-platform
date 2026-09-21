#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if [ ! -d venv ]; then
    echo "Virtual environment not found - running first-time setup..."
    ./setup.sh
fi

source venv/bin/activate

if [ ! -d chroma_db ]; then
    echo "Knowledge base not found - building it now..."
    python ingest.py
fi

echo "Starting JW Marriott Hotel Assistant..."
echo "A browser tab will open automatically. Press Ctrl+C to stop the app."
streamlit run app.py
