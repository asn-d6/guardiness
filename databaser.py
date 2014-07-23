#!/usr/bin/python

"""
Parse a bunch of consensus files and create an sqlite3 database with
the activity of all guard nodes during the past months.
"""

import logging
import argparse
import sys
import os
import sqlite3

import guardiness.consensus as consensus
import guardiness.sqlite_db as sqlite_db

SQLITE_DB_FILE = "./guardfraction.db"
SQLITE_DB_SCHEMA = "./db_schema.sql"

# XXX Fix this! ERROR:root:There was an error initializing the database. Maybe
# there is already a database in './guardiness.db'? The error message
# is 'table relays already exists'. Exiting.


def import_consensus_dir_to_db(db_cursor, consensus_dir, max_months,
                               delete_expired, delete_imported):
    """
    Read consensus files from 'consensus_dir' and write guard activity
    to the db at 'db_cursor'.
    """

    # Counter used to track progress.
    counter = 0
    # Initialize our singletons.
    consensus_parser = consensus.ConsensusParser(max_months)

    # Walk all files in the directory and try to parse them as
    # consensuses to import them to our database.
    dir_listing = os.listdir(consensus_dir)
    for filename in dir_listing:
        counter += 1
        logging.debug("Parsing consensus %s (%d/%d)!",
                      filename, counter, len(dir_listing))

        consensus_f = os.path.join(consensus_dir, filename)
        if not os.path.isfile(consensus_f): # skip non-files
            continue

        try:
            consensus_parser.parse_and_import_consensus(consensus_f, db_cursor)
        except consensus.DocumentExpired, err:
            logging.warning(u"Skipping expired consensus '%s'.", consensus_f)
            if delete_expired:
                os.remove(consensus_f)
            continue

        if delete_imported:
            os.remove(consensus_f)

def parse_cmd_args():
    parser = argparse.ArgumentParser("databaser.py",
                                      formatter_class = argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("consensus_dir", type=str,
                        help="Path to the consensus files directory.")
    parser.add_argument("max_months", type=int,
                        help="Consider only consensuses of the past max_months.")
    parser.add_argument("--db-file", type=str, default=SQLITE_DB_FILE,
                        help="Path to where the database file should be created .")
    parser.add_argument("--delete-expired", action="store_true", default=False,
                        help="Delete consensus files older than max_months.")
    parser.add_argument("--delete-imported", action="store_true", default=False,
                        help="Delete consensus files after importing them to the database.")
    parser.add_argument("--first-time", action="store_true", default=False,
                        help="First time running this script: initialize database, etc..")

    return parser.parse_args()

def main():
    """Read some consensus files and make a guard activity sqlite3 database."""

    logging.getLogger("").setLevel(logging.DEBUG) # XXX

    # Parse CLI
    args = parse_cmd_args()

    # Make sure a directory was provided.
    if not os.path.isdir(args.consensus_dir):
        logging.error("%s is not a directory!", args.consensus_dir)
        sys.exit(2)

    # Unwrap CLI arguments
    db_file = args.db_file
    consensus_dir = args.consensus_dir
    delete_expired = args.delete_expired
    delete_imported = args.delete_imported
    max_months = args.max_months
    first_time = args.first_time

    # Initialize sqlite3 database.
    db_conn, db_cursor = sqlite_db.init_db(db_file,
                                           SQLITE_DB_SCHEMA if first_time else None)

    # Parse all consensus files
    import_consensus_dir_to_db(db_cursor, consensus_dir, max_months,
                               delete_expired, delete_imported)

    # Commit database changes and close the file. We are done!
    db_conn.commit()
    db_conn.close()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logging.warning("Caught ^C. Closing.")
        sys.exit(1)

