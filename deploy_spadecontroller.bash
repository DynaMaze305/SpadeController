#!/bin/bash
# Implemented with assistance from AI (Copilot)
# Deployment script for SpadeController
LOGFILE=deploy.log
echo "$(date) - Deployment started" >> $LOGFILE

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_PATH="${SCRIPT_DIR}"

# Load .env file (local config for deployment)
ENV_FILE="${LOCAL_PATH}/.env"
if [ -f $ENV_FILE ]; then
    source $ENV_FILE
else
    echo "$ENV_FILE file not found" >> $LOGFILE
    exit 1
fi

# Validate required variables
REQUIRED_VARS=(REMOTE_USER REMOTE_PATH)
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "Error: $var is not set in $ENV_FILE" >> $LOGFILE
        exit 1
    fi
done

# Select bot to deploy on
read -p "Select bot to deploy on (1-4): " bot_choice
if [[ ! $bot_choice =~ ^[1-4]$ ]]; then
    echo "Invalid choice ${bot_choice}. Exiting." >> $LOGFILE
    exit 1
fi

REMOTE_HOST_VAR="REMOTE_HOST_${bot_choice}"
ROBOT_RECIPIENT_VAR="ROBOT_RECIPIENT_${bot_choice}"
XMPP_USERNAME_VAR="XMPP_USERNAME_${bot_choice}"
XMPP_PASSWORD_VAR="XMPP_PASSWORD_${bot_choice}"

REMOTE_HOST="${!REMOTE_HOST_VAR}"
ROBOT_RECIPIENT="${!ROBOT_RECIPIENT_VAR}"
XMPP_USERNAME="${!XMPP_USERNAME_VAR}"

# Validate bot-specific values
if [ -z "$REMOTE_HOST" ] || [ -z "$ROBOT_RECIPIENT" ] || [ -z "$XMPP_USERNAME" ]; then
    echo "Missing bot-specific configuration for bot ${bot_choice}" >> $LOGFILE
    exit 1
fi

# Generate .env file for the selected bot
TEMPLATE="${LOCAL_PATH}/.env.template"
OUTPUT="${LOCAL_PATH}/.env"

if [ ! -f "$TEMPLATE" ]; then
    echo "Missing .env.template in SpadeController" >> $LOGFILE
    exit 1
fi

cp "$TEMPLATE" "$OUTPUT"

sed -i "s|{{XMPP_USERNAME}}|$XMPP_USERNAME|g" "$OUTPUT"
sed -i "s|{{XMPP_PASSWORD}}|$XMPP_PASSWORD|g" "$OUTPUT"
sed -i "s|{{ROBOT_RECIPIENT}}|$ROBOT_RECIPIENT|g" "$OUTPUT"
sed -i "s|{{REMOTE_HOST}}|$REMOTE_HOST|g" "$OUTPUT"

echo "Generated .env for bot $bot_choice" >> $LOGFILE
# ---------------------------------------------------------

# Default values
SSH_PORT=${SSH_PORT:-22}
RSYNC_OPTS=${RSYNC_OPTS:--avz --delete}

echo "Deploying folder to ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}" >> $LOGFILE
echo "Using rsync options: ${RSYNC_OPTS}" >> $LOGFILE

# Confirm deployment
read -p "Proceed with deployment? (y/n) " confirm
[[ "$confirm" != "y" ]] && exit 0

# Run rsync
rsync ${RSYNC_OPTS} -e "ssh -p ${SSH_PORT}" \
    "${LOCAL_PATH}/" \
    "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/"

echo "Deployment complete." >> $LOGFILE
