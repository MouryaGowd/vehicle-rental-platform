#!/usr/bin/env bash
cd "$(dirname "$0")"

echo "Stopping JW Marriott Hotel Assistant..."

PIDS=$(pgrep -f "streamlit run app.py" || true)

if [ -z "$PIDS" ]; then
    echo "No running instance found."
    exit 0
fi

kill $PIDS
echo "Stopped."
