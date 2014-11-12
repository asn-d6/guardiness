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
import datetime

import guardiness.sqlite_db as sqlite_db
import guardiness.guard_ds as guard_ds

# XXX put it in const file
SQLITE_DB_FILE = "./guardfraction.db"
DEFAULT_OUTPUT_FNAME = "./guardfraction.output"

def read_db_file(db_conn, db_cursor, max_days, delete_expired=False):
    """
    Read database file with 'db_cursor' and register all guards active
    in the past 'max_days'.

    Return the Guards object that kept track of the guards, and the
    number of consensuses parsed.
    """
    # Keeps track of the guards we've seen.
    guards = guard_ds.Guards()

    # The months argument to datetime() so that we filter old consensuses.
    date_sql_parameter = "-%s days" % max_days

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

def find_missing_hours_from_list(date_list):
    """Given a list of datetimes, find which hours are missing."""
    hours_gap = (date_list[-1]-date_list[0]).total_seconds()/(60*60)

    all_hours_set = set(date_list[0]+ datetime.timedelta(hours=x) for x in range(int(hours_gap)))

    missing = sorted(all_hours_set - set(date_list))

    return missing


def print_missing_consensuses(db_conn, db_cursor, max_days):
    # The days argument to datetime() so that we filter old consensuses.
    date_sql_parameter = "-%s days" % max_days

    db_cursor.execute("SELECT consensus.consensus_date FROM consensus WHERE consensus.consensus_date >= (datetime('now', ?))", (date_sql_parameter,))
    sql_date_list = db_cursor.fetchall()

    # Get all the dates in a list
    consensus_date_list = []
    for date in sql_date_list:
        date_datetime = datetime.datetime.strptime(date[0], "%Y-%m-%d %H:%M:%S")
        consensus_date_list.append(date_datetime)
    logging.debug("These are all the dates we have: %s", str(consensus_date_list))

    # Find the missing hours and print them.
    missing_list = find_missing_hours_from_list(consensus_date_list)

    print "Here is a list of the missing consensuses:"
    for missing in missing_list:
        print "%s" % missing

def parse_cmd_args():
    parser = argparse.ArgumentParser("guardfraction.py",
                                      formatter_class = argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("max_days", type=int,
                        help="Only consider guards active in the past max_days.")
    parser.add_argument("--db-file", type=str, default=SQLITE_DB_FILE,
                        help="Path to the guard database file.")
    parser.add_argument("--delete-expired", action="store_true", default=False,
                        help="Delete expired database records based on max_days.")
    parser.add_argument("-o", "--output", type=str, default=DEFAULT_OUTPUT_FNAME,
                        help="Path to place the guardfraction output file.")
    parser.add_argument("-m", "--list-missing", action="store_true", default=False,
                        help="List any missing consensuses from the db and exit.")

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
    max_days = args.max_days
    db_file = args.db_file
    delete_expired = args.delete_expired
    list_missing = args.list_missing

    # Read database file and calculate guardfraction
    db_conn, db_cursor = sqlite_db.init_db(db_file)

    # Just print missing consensuses and bail
    if list_missing:
        print_missing_consensuses(db_conn, db_cursor, max_days)
        sys.exit(1)

    guards, consensuses_read_n = read_db_file(db_conn, db_cursor, max_days, delete_expired)

    # Caclulate guardfraction and write output file.
    try:
        guards.write_output_file(output_file, max_days, consensuses_read_n)
    except IOError, err:
        logging.warning("Could not write output file: %s", err)

    logging.info("Done! Wrote output file at %s.", output_file)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logging.warning("Caught ^C. Closing.")
        sys.exit(1)

