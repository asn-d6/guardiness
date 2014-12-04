CREATE TABLE relay (
  relay_id INTEGER PRIMARY KEY AUTOINCREMENT,
  identity BLOB NOT NULL,
  UNIQUE(identity)
);

CREATE TABLE consensus (
  consensus_id INTEGER PRIMARY KEY AUTOINCREMENT,
  consensus_date DATETIME NOT NULL,
   UNIQUE(consensus_date)
);

CREATE TABLE guarddata (
  relay_id INTEGER REFERENCES relay(relay_id) ON DELETE CASCADE NOT NULL,
  consensus_id INTEGER REFERENCES consensus(consensus_id) ON DELETE CASCADE NOT NULL
);

CREATE INDEX consensus_consensus_date_idx ON consensus(consensus_date);
CREATE INDEX guarddata_relay_id_idx ON guarddata(relay_id);
CREATE INDEX guarddata_consensus_id_idx ON guarddata(consensus_id);
