#!/bin/bash
set -eu
cd "$(dirname "$0")"

LOG_DIR="./logs"
DB_FILE="sessions.db"
PYTHON_ENV="${PYTHON_ENV:-python3}"
WPORT=5001

mkdir -p "$LOG_DIR"

echo "Checking database existence..."
if [ ! -f "$DB_FILE" ]; then
    echo "Database not found. Initializing..."
    "$PYTHON_ENV" -c "import db; db.HubDatabase().init_user()"
    echo "Database initialized."
else
    echo "Database found. Skipping initialization."
fi

echo "Starting Bluetooth receiver..."
nohup "$PYTHON_ENV" receiver.py >> "$LOG_DIR/receiver.log" 2>&1 &
echo "Receiver launched (PID $!); check $LOG_DIR/receiver.log for errors."

echo "Checking if port $WPORT is in use..."
if command -v lsof >/dev/null 2>&1 && lsof -i :"$WPORT" | grep LISTEN; then
    echo "!! Port $WPORT is already in use. Web server will NOT start!"
else
    echo " Port $WPORT is free. Starting Web Server..."
    nohup "$PYTHON_ENV" wserver.py >> "$LOG_DIR/wserver.log" 2>&1 &
    echo "Web server launched (PID $!); check $LOG_DIR/wserver.log for errors."
fi

echo "Startup commands dispatched."
