#!/usr/bin/python

"""
The guardfraction script reads the sqlite3 guard database and outputs
a file with the guardfraction of those guards.
"""

import datetime
import logging
import argparse
import sys
import os

import guardiness.sqlite_db as sqlite_db
import guardiness.guard_ds as guard_ds

# XXX put it in const file
SQLITE_DB_FILE = "./guardfraction.db"
DEFAULT_OUTPUT_FNAME = "./guardfraction.output"

def read_db_file(db_conn, db_cursor, max_months, delete_expired=False):
    """
    Read database file with 'db_cursor' and register all guards active
    in the past 'max_months'.

    Return the Guards object that kept track of the guards, and the
    number of consensuses parsed.
    """
    # Keeps track of the guards we've seen.
    guards = guard_ds.Guards()

    # The months argument to datetime() so that we filter old consensuses.
    date_sql_parameter = "-%s months" % max_months

    # If the user wants, remove old consensus measurements from the database.
    if delete_expired:
        db_cursor.execute("DELETE FROM consensus WHERE consensus_date < (datetime('now', ?))", (date_sql_parameter,))
        db_conn.commit()

    # Now we are ready to scrap the database!
    # First, get number of consensus documents read:
    db_cursor.execute("SELECT count(*) FROM consensus WHERE consensus.consensus_date >= (datetime('now', ?))", (date_sql_parameter,))
    consensuses_read_n = int(db_cursor.fetchone()[0])

    logging.info("Read db file with %d consensuses info", consensuses_read_n)
    # Check that there is at least a single consensus.  Not having any
    # consensuses might be the result of deleting too many consensuses
    # or improper database initialization.
    if consensuses_read_n == 0:
        logging.warning("No consensus measurements at all in the database.")
        return guards, 0

    # Get list of guards and their guardfraction
    db_cursor.execute("SELECT (SELECT identity FROM relay WHERE relay_id=guarddata.relay_id), count(*) FROM guarddata,consensus "
                      "WHERE consensus.consensus_date >= datetime('now', ?) AND consensus.consensus_id = guarddata.consensus_id GROUP BY relay_id;",
                      (date_sql_parameter,))
    guardfraction_list = db_cursor.fetchall()

    for guard_fpr, times_seen in guardfraction_list:
        guards.register_guard(guard_fpr, times_seen)
        logging.debug("Registered %s seen %d times", guard_fpr, times_seen)

    # Done. Close database and get out of here.
    db_conn.close()

    return guards, consensuses_read_n

def parse_cmd_args():
    parser = argparse.ArgumentParser("guardfraction.py",
                                      formatter_class = argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("max_months", type=int,
                        help="Only consider guards active in the past max_months.")
    parser.add_argument("--db-file", type=str, default=SQLITE_DB_FILE,
                        help="Path to the guard database file.")
    parser.add_argument("--delete-expired", action="store_true", default=False,
                        help="Delete expired database records based on max_months.")
    parser.add_argument("-o", "--output", type=str, default=DEFAULT_OUTPUT_FNAME,
                        help="Path to place the guardfraction output file.")

    return parser.parse_args()

def main():
    """
    Read an sqlite3 database and output guardfraction data.
    """

    # Enable this if you want debug logs
    # logging.getLogger("").setLevel(logging.DEBUG)

    # Parse CLI
    args = parse_cmd_args()

    output_file = args.output
    max_months = args.max_months
    db_file = args.db_file
    delete_expired = args.delete_expired

    # Read database file and calculate guardfraction
    db_conn, db_cursor = sqlite_db.init_db(db_file)
    guards, consensuses_read_n = read_db_file(db_conn, db_cursor, max_months, delete_expired)

    # Caclulate guardfraction and write output file.
    try:
        guards.write_output_file(output_file, max_months, consensuses_read_n)
    except IOError, err:
        logging.warning("Could not write output file: %s", err)

    logging.info("Done! Wrote output file at %s.", output_file)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logging.warning("Caught ^C. Closing.")
        sys.exit(1)

