-- Payments CRM Code All-Years Resolution Layer
-- Derived from payments_unified_staging only. Does not modify source tables.

-- =============================================================================
-- 1. payments_crm_code_all_years
-- One row per staging row; extracted code from patient_name_raw (final parentheses).
-- =============================================================================
CREATE TABLE IF NOT EXISTS payments_crm_code_all_years (
    id                            INTEGER PRIMARY KEY AUTOINCREMENT,
    payment_row_id                 INTEGER NOT NULL,   -- FK to payments_unified_staging.id
    source_file                    TEXT    NOT NULL,
    shamsi_year                    INTEGER NOT NULL,
    patient_name_raw               TEXT,
    patient_name_clean              TEXT,
    extracted_crm_code             TEXT,              -- digits from final parentheses
    record_no                      TEXT,
    extracted_code_equals_record_no_flag  INTEGER NOT NULL DEFAULT 0,  -- 1 if match
    parse_status                   TEXT    NOT NULL DEFAULT 'ok',     -- ok | no_code | error
    created_at                     TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (payment_row_id) REFERENCES payments_unified_staging(id)
);

CREATE INDEX IF NOT EXISTS idx_pccay_payment_row_id ON payments_crm_code_all_years(payment_row_id);
CREATE INDEX IF NOT EXISTS idx_pccay_shamsi_year ON payments_crm_code_all_years(shamsi_year);
CREATE INDEX IF NOT EXISTS idx_pccay_extracted_crm_code ON payments_crm_code_all_years(extracted_crm_code);
CREATE INDEX IF NOT EXISTS idx_pccay_equals_record_no ON payments_crm_code_all_years(extracted_code_equals_record_no_flag);


-- =============================================================================
-- 2. crm_code_financial_aggregate
-- One row per distinct extracted_crm_code; financial totals from net_received_raw.
-- =============================================================================
CREATE TABLE IF NOT EXISTS crm_code_financial_aggregate (
    crm_patient_code               TEXT    NOT NULL PRIMARY KEY,
    first_year                     INTEGER NOT NULL,
    last_year                      INTEGER NOT NULL,
    payment_rows_count              INTEGER NOT NULL DEFAULT 0,
    total_net_received             REAL    NOT NULL DEFAULT 0,
    positive_net_received_sum       REAL    NOT NULL DEFAULT 0,
    negative_net_received_sum       REAL    NOT NULL DEFAULT 0,
    distinct_patient_names_count    INTEGER NOT NULL DEFAULT 0,
    canonical_patient_name          TEXT,
    created_at                     TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_ccfa_first_year ON crm_code_financial_aggregate(first_year);
CREATE INDEX IF NOT EXISTS idx_ccfa_last_year ON crm_code_financial_aggregate(last_year);
