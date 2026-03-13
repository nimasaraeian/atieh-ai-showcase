-- Migration 021: phone_candidates table for Phone Normalization & Parsing Engine
-- Stores extracted phone candidates only. Does not modify existing patient tables.

CREATE TABLE IF NOT EXISTS phone_candidates (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    source_table         TEXT    NOT NULL,
    source_row_id        INTEGER NOT NULL,
    raw_phone            TEXT,
    primary_mobile       TEXT,
    secondary_mobile     TEXT,
    all_candidates       TEXT,   -- JSON array of raw candidate strings
    normalized_candidates TEXT,  -- JSON array or semicolon-separated canonical numbers
    confidence_score     REAL    NOT NULL DEFAULT 0,
    status               TEXT    NOT NULL,
    notes                TEXT,
    created_at           TEXT    DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_phone_candidates_source ON phone_candidates(source_table, source_row_id);
CREATE INDEX IF NOT EXISTS idx_phone_candidates_status ON phone_candidates(status);
CREATE INDEX IF NOT EXISTS idx_phone_candidates_primary ON phone_candidates(primary_mobile) WHERE primary_mobile IS NOT NULL;
