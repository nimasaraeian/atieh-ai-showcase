-- Migration 004: Payments staging table
-- Stores raw + normalised rows from payments_<YEAR>_full.xlsx files.

CREATE TABLE IF NOT EXISTS stg_payments (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,

    -- provenance
    import_run_id        TEXT    NOT NULL,   -- filename without extension
    file_name            TEXT    NOT NULL,
    sheet_name           TEXT,
    row_number           INTEGER NOT NULL,
    shamsi_year          INTEGER,            -- extracted from filename regex
    loaded_at            TEXT    NOT NULL,

    -- ETL status
    parse_status         TEXT    NOT NULL DEFAULT 'pending',  -- pending | ok | error
    parse_error          TEXT,

    -- raw extracted fields (stored verbatim from Excel)
    patient_name_raw     TEXT,
    phone_raw            TEXT,
    service_raw          TEXT,
    insurer_raw          TEXT,
    appointment_date_raw TEXT,
    amount_patient_raw   TEXT,
    amount_insurer_raw   TEXT,
    net_received_raw     TEXT,

    -- full row stored for debugging / reprocessing
    row_json             TEXT    NOT NULL,

    -- derived / normalised fields
    insurer_name_norm    TEXT,              -- text before first '('
    payer_source_norm    TEXT,              -- 'cash' | 'insurance' | 'unknown'
    patient_share_pct    INTEGER,           -- 0-100, or NULL
    pct_detected         INTEGER DEFAULT 0  -- 1 = found explicit '(NN %)'; 0 = defaulted
);

CREATE INDEX IF NOT EXISTS idx_stg_pay_import_run  ON stg_payments(import_run_id);
CREATE INDEX IF NOT EXISTS idx_stg_pay_status      ON stg_payments(parse_status);
CREATE INDEX IF NOT EXISTS idx_stg_pay_year        ON stg_payments(shamsi_year);
CREATE INDEX IF NOT EXISTS idx_stg_pay_payer       ON stg_payments(payer_source_norm);
