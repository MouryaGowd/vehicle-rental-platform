#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "=========================================="
echo " JW Marriott Hotel Assistant - First-time setup"
echo "=========================================="

PYTHON_BIN=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PYTHON_BIN="$candidate"
        break
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "[ERROR] Python 3.10+ was not found on PATH."
    echo "        Install it from https://www.python.org/downloads/ (or 'brew install python')"
    echo "        and re-run this script."
    exit 1
fi

if [ ! -d venv ]; then
    echo "Creating virtual environment..."
    "$PYTHON_BIN" -m venv venv
fi

source venv/bin/activate

echo "Installing dependencies (this can take a few minutes)..."
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "Building the hotel knowledge base..."
python ingest.py

echo
echo "Setup complete! Run ./run.sh to start the assistant."
