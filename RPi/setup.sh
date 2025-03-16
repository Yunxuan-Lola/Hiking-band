#!/bin/bash

LOG_DIR="./logs"
DB_FILE="sessions.db"
PYTHON_ENV="python"  # Modify if using a virtualenv

mkdir -p $LOG_DIR

echo "Checking database existence..."
if [ ! -f "$DB_FILE" ]; then
    echo "Database not found. Initializing..."
    $PYTHON_ENV -c "import db; db.HubDatabase().init_user()"
    echo "Database initialized."
else
    echo "Database found. Skipping initialization."
fi

echo "Starting Bluetooth receiver..."
while true; do
    $PYTHON_ENV receiver.py >> $LOG_DIR/receiver.log 2>&1
    echo "Receiver crashed. Restarting in 5 seconds..."
    sleep 5
done