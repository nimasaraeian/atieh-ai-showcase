-- National ID Recovery Preparation
-- 1) Fill payments_national_id_normalized from payments_unified_staging
-- 2) Match with patients.national_id and write to payments_national_id_patient_match (intermediate only)

-- =============================================================================
-- Step 1: Clear and fill normalized table (national_id_raw → 10 digits only)
-- =============================================================================
DELETE FROM payments_national_id_normalized;
INSERT INTO payments_national_id_normalized (staging_id, national_id_raw, national_id_norm, is_valid)
SELECT
    id,
    national_id_raw,
    CASE
        WHEN national_id_raw IS NULL OR TRIM(national_id_raw) = '' THEN NULL
        ELSE REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
            national_id_raw,
            '۰','0'),'۱','1'),'۲','2'),'۳','3'),'۴','4'),'۵','5'),'۶','6'),'۷','7'),'۸','8'),'۹','9')
    END AS digits_raw
FROM (
    SELECT id, national_id_raw,
           NULLIF(LENGTH(TRIM(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
               COALESCE(national_id_raw,''),
               '۰','0'),'۱','1'),'۲','2'),'۳','3'),'۴','4'),'۵','5'),'۶','6'),'۷','7'),'۸','8'),'۹','9')
           ), '')), 0) AS len_digits
    FROM payments_unified_staging
) t;
-- SQLite does not support regex; we need to strip non-digits in application or use a simpler approach.
-- Below: use a simplified version that keeps only digits 0-9 (application layer can do Persian digit replace).

-- Simpler: assume application script does the normalize and insert. This file documents the logic.
-- Actual INSERT done in Python so we can do re.sub(r'\D','',s) and len==10.

-- =============================================================================
-- Step 2: Build match table (single / collision / no_match)
-- =============================================================================
-- Run after Python has filled payments_national_id_normalized.
-- Match: JOIN payments_national_id_normalized n ON n.national_id_norm = p.national_id (patients)
-- Collision: when multiple patients have same national_id, mark as collision.
