BEGIN;

CREATE TABLE IF NOT EXISTS payment_identity_staging (
    staging_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT,
    receipt_no TEXT,
    record_no TEXT,
    patient_name_raw TEXT,
    mobile_raw TEXT,
    national_id_raw TEXT,
    admission_date_raw TEXT,
    net_received_raw TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pis_record_no
ON payment_identity_staging(record_no);

CREATE INDEX IF NOT EXISTS idx_pis_national_id_raw
ON payment_identity_staging(national_id_raw);

CREATE INDEX IF NOT EXISTS idx_pis_mobile_raw
ON payment_identity_staging(mobile_raw);

COMMIT;
