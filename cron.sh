#!/bin/bash

# This script is run every hour. It gets the latest consensus, imports
# it to the database and outputs a guardfraction output file.
# Please edit the definitions below to your liking:

# Where the guardfraction python script topdir is.
GUARDFRACTION_SRC=/home/user/guardiness/

# Where the consensuses and data are going to be stored
CONSENSUS_DIR=/home/user/test/consensus_dir

# Where the guardfraction output file should be placed.
GUARDFRACTION_OUTPUT_FILE=$CONSENSUS_DIR/guardfraction.output

# Create dir structure if it doesn't exist
mkdir -p $CONSENSUS_DIR/newest_consensus/
mkdir -p $CONSENSUS_DIR/all_consensus/

# Download latest consensus.
# XXX Should we clean the newest consensus dir first?
# XXX Replace this with a cp from DataDirectory or something.
torify wget http://128.31.0.39:9131/tor/status-vote/current/consensus -O $CONSENSUS_DIR/newest_consensus/consensus_`date +"%Y%m%d-%H%M%S"`

echo "[*] Downloaded latest consensus"

cd $GUARDFRACTION_SRC

# Import latest consensus to our database.
python databaser.py --db-file=$CONSENSUS_DIR/guardfraction.db $CONSENSUS_DIR/newest_consensus/ 3

echo "[*] Imported!"

# Move latest consensus to old consensuses dir
# XXX Do we even want to keep the old consensus around?
mv $CONSENSUS_DIR/newest_consensus/* $CONSENSUS_DIR/all_consensus/

# Calculate guardfraction
python guardfraction.py --db-file=$CONSENSUS_DIR/guardfraction.db --output=$GUARDFRACTION_OUTPUT_FILE 3

echo "[*] Done!"
