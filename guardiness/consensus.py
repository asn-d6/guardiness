import logging
import datetime

import stem
from stem.descriptor import parse_file, DocumentHandler

class ConsensusParser(object):
    """
    Singleton that parses consensuses and imports them to a database.
    """

    def __init__(self, max_months):
        """Initialize the consensus parser.

        'max_months' is the max number of months in the past we are willing to accept a consensus.
        """
        # Calculate oldest valid_after value that we would accept.
        now = datetime.datetime.now()
        max_months_in_seconds_timedelta = datetime.timedelta(0, max_months * 30 * 24 * 60 * 60)
        self.oldest_accepted_valid_after = now - max_months_in_seconds_timedelta

    def _check_consensus_date(self, valid_after):
        """
        Check that consensus with 'valid_after' hasn't expired.
        Raise DocumentExpired if it has.
        """
        if valid_after < self.oldest_accepted_valid_after:
            logging.warning("Summary file has too old valid-after: %s. " +
                            "Earliest accepted valid-after is %s.",
                            str(valid_after), str(self.oldest_accepted_valid_after))
            raise DocumentExpired

    def _router_is_guard(self, router):
        """Return true if the router is a guard according on its consensus flags."""
        return stem.Flag.GUARD in router.flags

    def parse_and_import_consensus(self, consensus_filename, db_cursor):
        """Parse consensus file and import it to the database at db_cursor"""

        with open(consensus_filename, 'rb') as consensus_fd:
            try:
                self._parse_and_import_consensus(consensus_fd, db_cursor)
            except (ValueError, IOError, UnicodeEncodeError), err:
                logging.warning(u"Can't parse %s because '%s'", consensus_filename, err) # XXX info?
                return

    def _parse_and_import_consensus(self, consensus_fd, db_cursor):
        """Friend of parse_and_import_consensus()."""

        # Use stem to parse the consensus.
        consensus =  parse_file(consensus_fd, 'network-status-microdesc-consensus-3 1.0',
                                document_handler = DocumentHandler.DOCUMENT).next()

        # Check that the document has not expired.
        self._check_consensus_date(consensus.valid_after)

        # XXX Protect against duplicate consensus?
        # Insert the consensus to the database
        db_cursor.execute("INSERT INTO consensus (consensus_date) VALUES (?)", (consensus.valid_after,))
        consensus_db_idx = db_cursor.lastrowid # note down the index of this consensus on the database

        """
        Register all the guard relays to the database
        and associate them with this consensus.
        """
        for router in consensus.routers.values():
            if not self._router_is_guard(router): # skip if not a guard
                continue

            identity = router.fingerprint
            relay_db_idx = None # the index of this relay on the database

            # Check if we've seen this guard before.
            # If it's a new guard, no row should be returned.
            row = db_cursor.execute("SELECT relay_id FROM relay WHERE identity=?", (identity,)).fetchone()

            if not row: # This is a new guard, register it!
                db_cursor.execute("INSERT INTO relay (identity) VALUES (?)", (identity,))
                relay_db_idx = db_cursor.lastrowid
                logging.debug("Inserted new guard %s", identity)
            else: # Seen this guard before, get its index.
                relay_db_idx = row['relay_id']

            # Associate this guard index with the consensus index in the database.
            db_cursor.execute("INSERT INTO guarddata (relay_id,consensus_id) VALUES (?,?)",
                              (relay_db_idx, consensus_db_idx))

class DocumentExpired(Exception): pass
