#!/bin/bash

set -u

# This script is run every hour. It gets the latest consensus, imports
# it to the database and outputs a guardfraction output file.
# Please edit the definitions below to your liking:

# Where the consensuses and data are going to be stored

#################################

GUARDFRACTION_SRC=$(dirname "$0")
GUARDFRACTION_SRC=$(readlink -f "$GUARDFRACTION_SRC")
STATE_DIR="$GUARDFRACTION_SRC/var"

DAYS_WORTH=90

if ! [ -d "$STATE_DIR" ]; then
        mkdir "$STATE_DIR"
fi

# Where the guardfraction output file should be placed.
GUARDFRACTION_OUTPUT_FILE="$STATE_DIR/guardfraction.output"

# Use flock to avoid parallel runs of the script
exec 9< "$STATE_DIR"
if ! flock -n -e 9; then
        echo >&5 "LOCK-ERROR"
        exit 1
fi

tmpdir=`mktemp -d "/tmp/guardfraction-XXXXXX"`
trap "rm -rf '$tmpdir'" EXIT

# Download latest consensus.
torify wget -q http://128.31.0.39:9131/tor/status-vote/current/consensus -O "$tmpdir/consensus"

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
python databaser.py --db-file="$STATE_DIR/guardfraction.db" "$tmpdir"

# Bail on error
if [ "$?" != 0 ]
then
    echo >&2 "Failed during database import."
    exit 1
fi

# echo "[*] Imported!"

# Calculate guardfraction
python guardfraction.py --db-file="$STATE_DIR/guardfraction.db" --output="$GUARDFRACTION_OUTPUT_FILE" "$DAYS_WORTH"

# Bail on error
if [ "$?" != 0 ]
then
    echo >&2 "Failed during guardfraction calculation."
    exit 1
fi

# echo "[*] Done!"

