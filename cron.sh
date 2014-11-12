#!/bin/bash

# This script is run every hour. It gets the latest consensus, imports
# it to the database and outputs a guardfraction output file.
# Please edit the definitions below to your liking:

# Where the guardfraction python script topdir is.
GUARDFRACTION_SRC=/home/user/guardiness/

# Where the consensuses and data are going to be stored
STATE_DIR=/home/user/test/consensus_dir

# Where the guardfraction output file should be placed (Change it!)
GUARDFRACTION_OUTPUT_FILE=$STATE_DIR/guardfraction.output

# Create dir structure if it doesn't exist
mkdir -p $STATE_DIR/newest_consensus/
mkdir -p $STATE_DIR/all_consensus/

# Download latest consensus.
# XXX Should we clean the newest consensus dir first?
# XXX Replace this with a cp from DataDirectory or something.
torify wget -q http://128.31.0.39:9131/tor/status-vote/current/consensus -O $STATE_DIR/newest_consensus/consensus_`date +"%Y%m%d-%H%M%S"` > /dev/null

# echo "[*] Downloaded latest consensus"

cd $GUARDFRACTION_SRC

# Import latest consensus to our database.
# (suppress any output because of cron job)
python databaser.py --db-file=$STATE_DIR/guardfraction.db $STATE_DIR/newest_consensus/ > /dev/null

# echo "[*] Imported!"

# Move latest consensus to old consensuses dir
# XXX Do we even want to keep the old consensus around?
mv $STATE_DIR/newest_consensus/* $STATE_DIR/all_consensus/

# Calculate guardfraction
python guardfraction.py --db-file=$STATE_DIR/guardfraction.db --output=$GUARDFRACTION_OUTPUT_FILE 90 > /dev/null

# echo "[*] Done!"

