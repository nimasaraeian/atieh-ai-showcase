CREATE TABLE IF NOT EXISTS engine_scoring_config (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO engine_scoring_config(key, value) VALUES
 ('FIN_MAX_BOOST', '12.0'),
 ('FIN_MAX_BOOST_IF_URGENT', '3.0');