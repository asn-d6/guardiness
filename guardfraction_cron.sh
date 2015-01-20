#!/bin/bash

set -u

# This script is run every hour. It gets the latest consensus, imports
# it to the database and outputs a guardfraction output file.
# Please edit the definitions below to your liking:

# Where the guardfraction python script topdir is.
GUARDFRACTION_SRC=/home/user/guardiness/

# Where the consensuses and data are going to be stored
STATE_DIR=/home/user/test/consensus_dir

#################################

DAYS_WORTH=90

# Where the guardfraction output file should be placed.
GUARDFRACTION_OUTPUT_FILE="$STATE_DIR/guardfraction.output"

# Where the newest consensus should be placed.
NEWEST_CONSENSUS_DIR="$STATE_DIR/newest_consensus/"

# Where the old consensuses should be placed.
CONSENSUS_ARCHIVE_DIR="$STATE_DIR/all_consensus/"

# Use flock to avoid parallel runs of the script
exec 9< "$STATE_DIR"
if ! flock -n -e 9; then
        echo >&5 "LOCK-ERROR"
        exit 1
fi

# Create dir structure if it doesn't exist
mkdir -p "$NEWEST_CONSENSUS_DIR"
mkdir -p "$CONSENSUS_ARCHIVE_DIR"

# Download latest consensus.
# XXX Replace this with a cp from DataDirectory or something.
# XXX cp "$DATA_DIRECTORY/cached-microdesc-consensus" "$NEWEST_CONSENSUS_DIR/consensus_`date +"%Y%m%d-%H%M%S"`"
torify wget -q http://128.31.0.39:9131/tor/status-vote/current/consensus -O "$NEWEST_CONSENSUS_DIR/consensus_$(date +"%Y%m%d-%H%M%S")"

# Bail on error
if [ "$?" != 0 ]
then
    echo >&2 "Failed while getting newest consensus."
    exit 1
fi

# echo "[*] Downloaded latest consensus"

cd "$GUARDFRACTION_SRC"

# Import latest consensus to our database.
# (suppress any output because of cron job)
python databaser.py --db-file="$STATE_DIR/guardfraction.db" "$NEWEST_CONSENSUS_DIR"

# Bail on error
if [ "$?" != 0 ]
then
    echo >&2 "Failed during database import."
    exit 1
fi

# echo "[*] Imported!"

# Move latest consensus to old consensuses dir
# XXX Do we even want to keep the old consensus around?
mv "$NEWEST_CONSENSUS_DIR"/* "$CONSENSUS_ARCHIVE_DIR"

# Calculate guardfraction
python guardfraction.py --db-file="$STATE_DIR/guardfraction.db" --output="$GUARDFRACTION_OUTPUT_FILE" "$DAYS_WORTH"

# Bail on error
if [ "$?" != 0 ]
then
    echo >&2 "Failed during guardfraction calculation."
    exit 1
fi

# echo "[*] Done!"

