#!/usr/bin/env bash
# run_device.sh
PROJECT_FOLDER=$(pwd)

if test -f "$PROJECT_FOLDER/.venv/Scripts/activate"; then
    source $PROJECT_FOLDER/.venv/Scripts/activate
else
    source $PROJECT_FOLDER/venv/Scripts/activate
fi

if [ "$COMMAND" != "" ]; then
    python -m src.main --device-id "$DEVICE_ID" --command="$COMMAND"
else
    echo "No command provided. Stopping device $DEVICE_ID"
    sleep 10
    exit 0
fi
