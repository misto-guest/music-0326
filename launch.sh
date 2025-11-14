#!/bin/bash
set -e

# Initialize variables
PROJECT_FOLDER=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -W 2>/dev/null || pwd)
# Convert to Windows path if running in Git Bash
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    PROJECT_FOLDER=$(cygpath -w "$PROJECT_FOLDER" 2>/dev/null || echo "$PROJECT_FOLDER")
fi

PROJECT_FOLDER=${PROJECT_FOLDER//\\//}
LOGS_FOLDER="${PROJECT_FOLDER}/logs"
PM2_CONFIG_FILE="${PROJECT_FOLDER}/ecosystem.config.js"
DEVICES_FILE="${PROJECT_FOLDER}/devices.list"

echo "PROJECT_FOLDER: $PROJECT_FOLDER"
echo "LOGS_FOLDER: $LOGS_FOLDER"
echo "PM2_CONFIG_FILE: $PM2_CONFIG_FILE"
echo "DEVICES_FILE: $DEVICES_FILE"
echo ""

# Load device IDs from external file
load_devices() {
    if [[ ! -f "$DEVICES_FILE" ]]; then
        echo "Error: Devices file not found at $DEVICES_FILE"
        echo "Please create a file named 'devices.list' in the project root with one device ID per line."
        exit 1
    fi
    
    # Read non-empty, non-comment lines into DEVICES array
    mapfile -t DEVICE_LINES < <(grep -v '^\s*#' "$DEVICES_FILE" | grep -v '^\s*$' | tr -d '\r')
    
    if [[ ${#DEVICE_LINES[@]} -eq 0 ]]; then
        echo "Error: No valid device IDs found in $DEVICES_FILE"
        echo "Please add device IDs (one per line) to the file."
        exit 1
    fi
    
    echo "Loaded ${#DEVICE_LINES[@]} device(s) from $DEVICES_FILE"
}

get_app_name_by_device_num() {
    NUM=$1
    if [[ ${#NUM} == 1 ]]; then
        NUM="0$NUM"
    fi
    for DEVICE_LINE in "${DEVICE_LINES[@]}"; do
        IFS=',' read -r ID DEVICE_ID COMMAND <<< "$DEVICE_LINE"
        if [[ $ID == $NUM ]]; then
            # Remove quotes around COMMAND if present
            COMMAND=${COMMAND//\"/}
            CMD_TXT=${COMMAND// /_}
            NAME_TXT="#${ID}-${DEVICE_ID}-${CMD_TXT}"
            echo "$NAME_TXT"
            return
        fi
    done
}

# Generate PM2 ecosystem configuration
generate_pm2_config() {
    echo "Generating PM2 configuration for ${#DEVICE_LINES[@]} devices..."

    local config_content='module.exports = {
  apps: ['

    for DEVICE_LINE in "${DEVICE_LINES[@]}"; do
        IFS=',' read -r ID DEVICE_ID COMMAND <<< "$DEVICE_LINE"

        # Remove quotes around COMMAND if present
        COMMAND=${COMMAND//\"/}
        CMD_TXT=${COMMAND// /_}
        NAME_TXT=$(get_app_name_by_device_num $ID)

        config_content+="
    {
      name: '$NAME_TXT',
      script: './run_device.sh',
      args: '',
      max_memory_restart: '1G',
      autorestart: false,
      max_restarts: 10,
      restart_delay: 2000,
      output: '${LOGS_FOLDER//\/\\}/${DEVICE_ID}.log',
      error: '${LOGS_FOLDER//\/\\}/${DEVICE_ID}.log',
      watch: false,
      env: {
        DEVICE_ID: '${DEVICE_ID}',
        COMMAND: '${COMMAND}',
        PYTHONUNBUFFERED: '1',
        PYTHONIOENCODING: 'utf-8'
      }
      
    },"
    done

    # Remove trailing comma and close the array
    config_content="${config_content%,}
  ]
};"

    echo "$config_content" > "$PM2_CONFIG_FILE"
    echo "Generated PM2 configuration at $PM2_CONFIG_FILE with ${#DEVICE_LINES[@]} devices"
}

# Start all instances
start_instances() {
    # Install PM2 if not installed
    if ! command -v pm2 &> /dev/null; then
        echo "PM2 not found. Installing PM2..."
        npm install -g pm2
        pm2 install pm2-logrotate
    fi

    pm2 set pm2-logrotate:rotateInterval '0 0 * * *' > /dev/null  # rotate daily
    pm2 set pm2-logrotate:retain 30 > /dev/null                     # keep 7 old logs
    pm2 set pm2-logrotate:compress true > /dev/null                # compress old logs
    pm2 set pm2-logrotate:max_size 200M > /dev/null                # or rotate when >50M
    pm2 set pm2-logrotate:dateFormat 'YYYY-MM-DD' > /dev/null

    # Generate or update config
    generate_pm2_config

    # Start all processes using the config file
    cd "$PROJECT_FOLDER"
    pm2 start "$PM2_CONFIG_FILE"

    # Save PM2 process list
    pm2 save
    echo "Run 'pm2 startup' to enable auto-start on boot"
}

# Stop all instances
stop_instances() {
    pm2 delete all
    pm2 save
}

# Show status
show_status() {
    pm2 status
}

# Restart one instance by device index
restart_by_device_num() {
    ID=$1
    if [[ ${#ID} == 1 ]]; then
        ID="0$ID"
    fi
    if [ -z "$ID" ]; then
        echo "Missing device ID"
        echo "Usage: $0 restart-by-id <device_id>"
        exit 1
    fi
    ID_TXT="#$ID-"
    pm2_id=$(pm2 list | grep "$ID_TXT" | awk '{print $2}' | head -n 1)
    if [ -z "$pm2_id" ]; then
        echo "No instance running for device ID: $ID"
        exit 1
    fi

    generate_pm2_config

    NAME=$(get_app_name_by_device_num $ID)
    echo "Restarting instance $pm2_id: $NAME"
    pm2 restart "$pm2_id" --name "$NAME" 
}

# Main script execution
load_devices

case "$1" in
    start)
        start_instances
        ;;
    stop)
        stop_instances
        ;;
    restart)
        stop_instances
        start_instances
        ;;
    restart-by-num)
        restart_by_device_num "$2"
        ;;
    status)
        show_status
        ;;
    generate-config)
        generate_pm2_config
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|generate-config}"
        echo "  start          - Start all instances"
        echo "  stop           - Stop all instances"
        echo "  restart        - Restart all instances"
        echo "  restart-by-num  - Restart one instance by device num"
        echo "  status         - Show status"
        echo "  generate-config - Regenerate PM2 config file"
        exit 1
        ;;
esac

exit 0