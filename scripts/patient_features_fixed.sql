-- Fix patient_features: avoid negative tenure, handle single-visit frequency, keep last_visit_days (negative = future)
-- Run: sqlite3 atieh_clinic.db < scripts/patient_features_fixed.sql

DROP TABLE IF EXISTS patient_features;

CREATE TABLE patient_features (
    patient_id INTEGER PRIMARY KEY,
    visits_total INTEGER,
    tenure_days INTEGER,
    last_visit_days INTEGER,
    lifetime_value REAL,
    frequency REAL
);

INSERT INTO patient_features
SELECT
    patient_id,
    COUNT(*) AS visits_total,
    CAST(
        julianday(MAX(appointment_date)) - julianday(MIN(appointment_date))
    AS INTEGER) AS tenure_days,
    CAST(
        julianday('now') - julianday(MAX(appointment_date))
    AS INTEGER) AS last_visit_days,
    SUM(COALESCE(final_amount_paid, 0)) AS lifetime_value,
    CASE
        WHEN julianday(MAX(appointment_date)) - julianday(MIN(appointment_date)) <= 0
        THEN CAST(COUNT(*) AS REAL)
        ELSE COUNT(*) / (julianday(MAX(appointment_date)) - julianday(MIN(appointment_date)))
    END AS frequency
FROM appointments
GROUP BY patient_id;

-- Top by visits (meaningful until final_amount_paid is backfilled)
-- SELECT * FROM patient_features ORDER BY visits_total DESC LIMIT 10;
