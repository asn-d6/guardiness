#!/bin/bash

set -u
set -e

# This script is run every hour. It gets the latest consensus, imports
# it to the database and outputs a guardfraction output file.

##################################################################

GUARDFRACTION_SRC=$(dirname "$0")
GUARDFRACTION_SRC=$(readlink -f "$GUARDFRACTION_SRC")
STATE_DIR="" # defaults to $GUARDFRACTION_SRC/var
GUARDFRACTION_OUTPUT_FILE="" # defaults to :$STATE_DIR/guardfraction.output

WGET_PREFIX="" # one option might be "torify"
CONSENSUS_SOURCE="http://128.31.0.39:9131/tor/status-vote/current/consensus"

DAYS_WORTH=90

VERBOSE=${VERBOSE:-0}

# You can override any of the above variables in ~/.guardfraction.conf
[ -e ~/.guardfraction.conf ] && . ~/.guardfraction.conf

##################################################################

[ "$VERBOSE" -gt 1 ] &&  set -x

STATE_DIR="${STATE_DIR:-$GUARDFRACTION_SRC/var}"
GUARDFRACTION_OUTPUT_FILE="${GUARDFRACTION_OUTPUT_FILE:-$STATE_DIR/guardfraction.output}"

if ! [ -d "$STATE_DIR" ]; then
        mkdir "$STATE_DIR"
fi

# Use flock to avoid parallel runs of the script
exec 9< "$STATE_DIR"
if ! flock -n -e 9; then
        echo >&2 "Could not acquire lock on $STATE_DIR."
        exit 1
fi

tmpdir=`mktemp -d "/tmp/guardfraction-XXXXXX"`
trap "rm -rf '$tmpdir'" EXIT

# Download latest consensus.
if ! $WGET_PREFIX wget -q "$CONSENSUS_SOURCE" -O "$tmpdir/consensus"
then
    echo >&2 "Failed while getting newest consensus."
    exit 1
fi

[ "$VERBOSE" -gt 0 ] &&  echo "[*] Downloaded latest consensus"

cd "$GUARDFRACTION_SRC"

# Import latest consensus to our database.
# (suppress any output because of cron job)
if ! python databaser.py --db-file="$STATE_DIR/guardfraction.db" "$tmpdir"
then
    echo >&2 "Failed during database import."
    exit 1
fi

[ "$VERBOSE" -gt 0 ] && echo "[*] Imported!"

# Calculate guardfraction
if ! python guardfraction.py --db-file="$STATE_DIR/guardfraction.db" --output="$GUARDFRACTION_OUTPUT_FILE" "$DAYS_WORTH"
then
    echo >&2 "Failed during guardfraction calculation."
    exit 1
fi

[ "$VERBOSE" -gt 0 ] && echo "[*] Done!"
