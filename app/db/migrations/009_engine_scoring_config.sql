-- 009_engine_scoring_config.sql
CREATE TABLE IF NOT EXISTS engine_scoring_config (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO engine_scoring_config(key, value) VALUES
 ('FIN_WEIGHT', '0.20'),              -- وزن مالی در حالت عادی
 ('FIN_WEIGHT_IF_URGENT', '0.05'),    -- سقف/وزن مالی وقتی urgent است
 ('FIN_SCORE_MAX', '100');            -- اگر لازم شد cap کنیم