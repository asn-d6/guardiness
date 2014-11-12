import unittest
import os

import guardiness.sqlite_db as sqlite_db
import tempfile
import guardfraction

SQLITE_DB_FILE = ":memory:"
SQLITE_DB_SCHEMA = "./db_schema.sql"

GUARD_1_FPR = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
GUARD_2_FPR = "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
GUARD_3_FPR = "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"
GUARD_4_FPR = "DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD"

def populate_db_helper(db_cursor):
    """
    Populate the database at 'db_cursor' with some test data.

    In the end, the database should contain 3 consensuses and 4 guards in this way:
     * consensus_1 contains (guard_1, guard_2, guard_3)
     * consensus_2 contains (guard_1, guard_2)
     * consensus_3 contains (guard_1, guard_4)
    """

    # Create the consensuses
    db_cursor.execute("INSERT INTO consensus (consensus_date) VALUES (datetime('now', '-1 day'))")
    first_consensus_idx = db_cursor.lastrowid
    db_cursor.execute("INSERT INTO consensus (consensus_date) VALUES (datetime('now', '-1 month'))")
    second_consensus_idx = db_cursor.lastrowid
    db_cursor.execute("INSERT INTO consensus (consensus_date) VALUES (datetime('now', '-1 month', '-1 hours'))")
    third_consensus_idx = db_cursor.lastrowid

    # Create the guards
    db_cursor.execute("INSERT INTO relay (identity) VALUES (?)", (GUARD_1_FPR,))
    first_guard_idx = db_cursor.lastrowid
    db_cursor.execute("INSERT INTO relay (identity) VALUES (?)", (GUARD_2_FPR,))
    second_guard_idx = db_cursor.lastrowid
    db_cursor.execute("INSERT INTO relay (identity) VALUES (?)", (GUARD_3_FPR,))
    third_guard_idx = db_cursor.lastrowid
    db_cursor.execute("INSERT INTO relay (identity) VALUES (?)", (GUARD_4_FPR,))
    fourth_guard_idx = db_cursor.lastrowid

    # Populate first consensus
    db_cursor.execute("INSERT INTO guarddata (relay_id,consensus_id) VALUES (?,?)",
                      (first_guard_idx, first_consensus_idx))
    db_cursor.execute("INSERT INTO guarddata (relay_id,consensus_id) VALUES (?,?)",
                      (second_guard_idx, first_consensus_idx))
    db_cursor.execute("INSERT INTO guarddata (relay_id,consensus_id) VALUES (?,?)",
                      (third_guard_idx, first_consensus_idx))

    # Populate second consensus
    db_cursor.execute("INSERT INTO guarddata (relay_id,consensus_id) VALUES (?,?)",
                      (first_guard_idx, second_consensus_idx))
    db_cursor.execute("INSERT INTO guarddata (relay_id,consensus_id) VALUES (?,?)",
                      (second_guard_idx, second_consensus_idx))

    # Populate third consensus
    db_cursor.execute("INSERT INTO guarddata (relay_id,consensus_id) VALUES (?,?)",
                      (first_guard_idx, third_consensus_idx))
    db_cursor.execute("INSERT INTO guarddata (relay_id,consensus_id) VALUES (?,?)",
                      (fourth_guard_idx, third_consensus_idx))


class testGuardFraction(unittest.TestCase):
    def test_guardfraction_from_db(self):
        """Test that the guardfraction script understands the database correctly."""

        # Initialize the database and populate it with some test data
        db_conn, db_cursor = sqlite_db.init_db(SQLITE_DB_FILE, SQLITE_DB_SCHEMA)
        populate_db_helper(db_cursor)
        db_conn.commit()

        # Now read the database using the guardfraction script.
        # (don't care about dates. that's for the next test to worry about
        guards, consensuses_read_n = guardfraction.read_db_file(db_conn, db_cursor, 999)

        # Now make sure that guardfraction understood the correct data.

        self.assertEquals(consensuses_read_n, 3)
        self.assertEquals(len(guards.guards), 4)
        # Check the times_seen for each guard.
        for guard_fpr, guard in guards.guards.items():
            if guard_fpr == GUARD_1_FPR:
                self.assertEquals(guard.times_seen, 3)
            elif guard_fpr == GUARD_2_FPR:
                self.assertEquals(guard.times_seen, 2)
            elif guard_fpr == GUARD_3_FPR:
                self.assertEquals(guard.times_seen, 1)
            elif guard_fpr == GUARD_4_FPR:
                self.assertEquals(guard.times_seen, 1)
            else:
                self.assertTrue(False) # Unknown guard!

        db_conn.close()

    def test_output_file(self):
        """
        Using the test database again, test that the guardfraction
        script spits out the correct guardfraction output file.
        """

        # Initialize the database and populate it with some test data
        db_conn, db_cursor = sqlite_db.init_db(SQLITE_DB_FILE, SQLITE_DB_SCHEMA)
        populate_db_helper(db_cursor)
        db_conn.commit()

        # Read the database
        guards, consensuses_read_n = guardfraction.read_db_file(db_conn, db_cursor, 999)

        # Make a tempfile to save the output file.
        temp_file, temp_path = tempfile.mkstemp()
        os.close(temp_file)
        guards.write_output_file(temp_path, 999, consensuses_read_n)

        # Open the output file and validate its contents.
        with open(temp_path) as test_fd:
            lines = test_fd.readlines()

            # One line for the header, one line for n-inputs and 4 guards
            self.assertEquals(len(lines), 6)

            # Test the n-inputs line
            self.assertEquals(lines[1], "n-inputs 3 999 23976\n")

            # Test guard lines
            self.assertIn("guard-seen AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA 100 3\n", lines[2:])
            self.assertIn("guard-seen BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB 67 2\n", lines[2:])
            self.assertIn("guard-seen CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC 33 1\n", lines[2:])
            self.assertIn("guard-seen DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD 33 1\n", lines[2:])

        db_conn.close()

if __name__ == '__main__':
    unittest.main()
