#!/usr/bin/env bash
# run_device.sh
PROJECT_FOLDER=$(pwd)

if test -f "$PROJECT_FOLDER/.venv/Scripts/activate"; then
    source $PROJECT_FOLDER/.venv/Scripts/activate
else
    source $PROJECT_FOLDER/venv/Scripts/activate
fi

python -m src.main --device-id "$DEVICE_ID" --command="sall --exclude amazon youtube"
