#!/bin/bash
PROJECT_FOLDER="C:\Users\windows2025\PycharmProjects\android_music_automation"
LOGS_FOLDER=$PROJECT_FOLDER/logs

DEVICES=(
    "R3CR707G1FF"
    "R5CR11KHW4W"
    "RFCT512BG1D"
    "R5CR128DBWB"
    "R5CR80RMVXD"
    "R5CR70V8SFR"
    "R5CR92M73NN"
    "R3CR202S10A"
    "R5CR71C2VNK"
    "R5CR60LS9JX"
    "R3CR100RZM"
    "R5CR70V87SL"
    "R5CR2JA5NK"
    "R5CNC0RZS"
    "R5CR70SM7"
    "R5CR38FN7"
    "R5CRB2FP6"
    "R5CR70MQ7"
    "R5CT50CDE"
    "R5CR32LFM"
    "R5CW51LEZ"
    "R3CT30KY9"
    "R5CT43BZM"
    "R5CT236E8"
    "R5CT92RTM"
    "R5CTA12FWX"
    "R5CT92M9K"
    "R5CT50NEZ"
    "R5CT814PWZ"
    "RFCT90N0EG"
    "R5CT21MP7"
    "R5CT10Y99"
    "R5CT311ZY"
    "R5CW22ML4"
    "RFCTA0YDHS"
    "R5CT61PDQD"
    "R5CT50BAK"
)

function launch_one_device() {
    DEVICE_ID=$1
    mkdir -p $LOGS_FOLDER/$DEVICE_ID
    python -m src.main --device-id $DEVICE_ID --command="sall --exclude amazon youtube" >> $LOGS_FOLDER/$DEVICE_ID/$(date +"%Y-%m-%d").log 2>&1 &
}

source $PROJECT_FOLDER/.venv/Scripts/activate
for DEVICE_ID in "${DEVICES[@]}"; do
    launch_one_device "$DEVICE_ID"
done