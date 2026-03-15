-- Patient insurance profile: aggregated from payments_unified_staging.insurer_raw per crm_patient_code.
-- Read-only source: payments_unified_staging (no modification to staging).
-- Populated by: scripts/build_patient_insurance_profile.py

CREATE TABLE IF NOT EXISTS patient_insurance_profile (
    crm_patient_code          TEXT    NOT NULL PRIMARY KEY,
    most_frequent_insurer     TEXT,
    most_recent_insurer       TEXT,
    distinct_insurers_count   INTEGER NOT NULL DEFAULT 0,
    updated_at                TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_pip_crm_code ON patient_insurance_profile(crm_patient_code);
