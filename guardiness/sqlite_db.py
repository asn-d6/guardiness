import sqlite3
import sys
import logging

def init_db(db_filename, schema_filename=None):
    """
    Initialize the sqlite3 database at 'db_filename'.
    Exit with an informative message if any fatal errors occur.

    If a 'schema_filename' is provided, it's a file with SQL commands
    that load the database schema.
    """

    # Initialize the database
    try:
        db_conn = sqlite3.connect(db_filename,
                                  timeout = 900,# XXX timeout?
                                  detect_types = sqlite3.PARSE_DECLTYPES + sqlite3.PARSE_COLNAMES)
    except sqlite3.OperationalError, err:
        logging.error("Error connecting to the database. " +
                      "Maybe you don't have permissions or '%s' point " +
                      "to a nonexistent file? The error message is '%s'. " +
                      "Exiting.", db_filename, err)
        sys.exit(3)

    db_conn.row_factory = sqlite3.Row
    db_cursor = db_conn.cursor()

    # Enable foreign key constraints (disabled by default on sqlite3...)
    db_cursor.execute('pragma foreign_keys=ON')

    # If a schema file was provided, load it up.
    if schema_filename:
        with open(schema_filename) as schema_fd:
            sql_schema = schema_fd.read()
            try:
                db_conn.executescript(sql_schema)
            except sqlite3.OperationalError, err:
                logging.error("There was an error initializing the database. " +
                              "Maybe there is already a database in '%s'? " +
                              "The error message is '%s'. Exiting.",
                              db_filename, err)
                sys.exit(4)

    return db_conn, db_cursor
