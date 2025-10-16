#!/bin/bash
PROJECT_FOLDER=$(pwd)
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
    "R3CR100RZMH"
    "R5CR70V87SL"
    "R5CRC2JA5NK"
    "R5CNC0RZSNW"
    "R5CR70SM7WR"
    "R5CRC38FN7N"
    "R5CRB2FP6PL"
    "R5CR70MQ79H"
    "R5CT50CDEQF"
    "R5CR32LFMMN"
    "R5CW51LEZVP"
    "R3CT30KY99D"
    "R5CT43BZMRR"
    "R5CT236E85J"
    "R5CT92RTMYT"
    "R5CTA12FWXW"
    "R5CT92M9KZN"
    "R5CT50NE2ZL"
    "R5CT814PWZP"
    "RFCT90N0EGZ"
    "R5CT21MP78W"
    "R5CT10Y99HK"
    "R5CT311ZYXA"
    "R5CW22ML4ZE"
    "RFCTA0YDH6H"
    "R5CT61PDQDV"
    "R5CT50BAKEB"
)

function launch_one_device() {
    DEVICE_ID=$1
    mkdir -p $LOGS_FOLDER/$DEVICE_ID
    python -m src.main --device-id $DEVICE_ID --command="sall --exclude amazon youtube" >> $LOGS_FOLDER/$DEVICE_ID/$(date +"%Y-%m-%d").log 2>&1 &
}


if test -f "$PROJECT_FOLDER/.venv/Scripts/activate"; then
    source $PROJECT_FOLDER/.venv/Scripts/activate
else
    source $PROJECT_FOLDER/venv/Scripts/activate
fi

for DEVICE_ID in "${DEVICES[@]}"; do
    launch_one_device "$DEVICE_ID"
done