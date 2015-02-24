#!/bin/bash

set -u
set -e

# This script is run every hour. It gets the latest consensus, imports
# it to the database and outputs a guardfraction output file.

##################################################################

# Source directory of this script
GUARDFRACTION_SRC=$(dirname "$0")
GUARDFRACTION_SRC=$(readlink -f "$GUARDFRACTION_SRC")

# Directory where the database and output of this script will be saved
# on. Make sure you have write access to it. Defaults to $GUARDFRACTION_SRC/var .
STATE_DIR=""

# Filename of the output file. This is the file that Tor should read.
# Defaults to: $STATE_DIR/guardfraction.output
GUARDFRACTION_OUTPUT_FILE=""

WGET_PREFIX="" # one option might be "torify"

# Where to fetch the consensus from. This should be set in the
# configuration file. Please set it to something like:
# CONSENSUS_SOURCE=http://128.31.0.39:9131/tor/status-vote/current/consensus
CONSENSUS_SOURCE=""

# How many days of consensuses should we consider? This should be
# equal to the guard lifetime period. Leave it as is for now.
DAYS_WORTH=90

# Set to 1 if you want verbose output.
VERBOSE=${VERBOSE:-0}

# Please override CONSENSUS_SOURCE and any other of the above
# variables in ~/.guardfraction.conf .
[ -e ~/.guardfraction.conf ] && . ~/.guardfraction.conf

##################################################################

[ "$VERBOSE" -gt 0 ] &&  echo "[*] Starting up"

if [ -z "$CONSENSUS_SOURCE" ]; then
    echo >&2 "No CONSENSUS_SOURCE set. Please set CONSENSUS_SOURCE in ~/.guardfraction.conf."
    echo >&2 " e.g.  CONSENSUS_SOURCE=http://128.31.0.39:9131/tor/status-vote/current/consensus"
    exit 1
fi

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

[ "$VERBOSE" -gt 0 ] &&  echo "[*] About to download consensus"

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
