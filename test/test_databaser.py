import unittest
import os

import stem
from stem.descriptor import parse_file, DocumentHandler

import guardiness.sqlite_db as sqlite_db
import databaser

SQLITE_DB_FILE = ":memory:"
SQLITE_DB_SCHEMA = "./db_schema.sql"

TEST_CONSENSUSES_DIR = "./test/test_consensuses/" # XXX

def parse_consensuses_naive_way(consensus_dir):
    """
    Parses a bunch of consensuses in a naive manner, and marks how many
    times each guard has appeared in those consensuses.
    """

    # A dictionary mapping <guard fingerprints> to <times seen in consensus>
    guards_dict  = {}

    # Walk all files in the consensus directory and try to parse them
    # and import them to our database.
    dir_listing = os.listdir(consensus_dir)
    for f in dir_listing:
        consensus_f = os.path.join(consensus_dir, f)

        if not os.path.isfile(consensus_f): # skip non-files
            continue

        # Parse consensus
        consensus =  parse_file(consensus_f, 'network-status-microdesc-consensus-3 1.0',
                                document_handler = DocumentHandler.DOCUMENT).next()

        # For every guard:
        # * If we see it for the first time, initialize its counter to 1.
        # * If we've seen it before, increment its counter by one.
        for router in consensus.routers.values():
            if stem.Flag.GUARD in router.flags: # It's a guard
                if router.fingerprint not in guards_dict:
                    # First time we see this guard.
                    guards_dict[router.fingerprint] = 1
                else:
                    # Seen this guard before, increment counter by one
                    guards_dict[router.fingerprint] += 1

    return guards_dict

class testDatabaser(unittest.TestCase):
    def test_database_import(self):
        """Check that consensuses are parsed and imported to the db properly.

        Import a directory of consnensuses using the databaser
        function, and also import them using a naive but simple
        way. Then cross-check the results to see that they match.
        """

        # Import the consensus directory to the database using databaser
        db_conn, db_cursor = sqlite_db.init_db(SQLITE_DB_FILE, SQLITE_DB_SCHEMA)
        databaser.import_consensus_dir_to_db(db_cursor, TEST_CONSENSUSES_DIR, False)
        db_conn.commit()

        # Now parse the same consensus directory with the naive algorithm.
        guards_dict = parse_consensuses_naive_way(TEST_CONSENSUSES_DIR)

        # Now assert that results match.
        # FIrst of all, check that the right number of consensuses were parsed
        db_cursor.execute("SELECT count(*) FROM consensus")
        consensuses_read_n = int(db_cursor.fetchone()[0])
        self.assertEquals(consensuses_read_n, 4)

        # Now get the list of guards and their guardiness from the
        # database, and compare it with the naive guards dictionary.
        db_cursor.execute("SELECT (SELECT identity FROM relay WHERE relay_id=guarddata.relay_id), count(*) FROM guarddata GROUP BY relay_id;")
        guardiness_list = db_cursor.fetchall()

        self.assertEquals(len(guardiness_list), len(guards_dict))

        # Individually for each guard make sure the times_seen is the same.
        for guard_fpr, times_seen in guardiness_list:
            # The silly parsing function should have seen this fpr
            self.assertIn(guard_fpr, guards_dict)
            # Make sure that the same number of guard observations were found
            self.assertEquals(guards_dict[guard_fpr], times_seen)

if __name__ == '__main__':
    unittest.main()
