BEGIN;

DELETE FROM identity_patient_features;

WITH patient_base AS (
    SELECT
        p.id,
        p.name,
        p.phone,
        p.first_visit_date,

        TRIM(
            REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                LOWER(COALESCE(p.name, '')),
                'ي', 'ی'),
                'ك', 'ک'),
                '  ', ' '),
                '  ', ' '),
                '  ', ' ')
        ) AS name_norm_raw,

        TRIM(
            REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
            REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                LOWER(COALESCE(p.phone, '')),
                ' ', ''), '-', ''), '(', ''), ')', ''), '+', ''),
                '۰','0'), '۱','1'), '۲','2'), '۳','3'), '۴','4'),
                '۵','5'), '۶','6'), '۷','7'), '۸','8'), '۹','9')
        ) AS phone_norm_raw
    FROM patients p
),
patient_clean AS (
    SELECT
        pb.id,
        pb.name,
        pb.first_visit_date,
        pb.name_norm_raw,

        CASE
            WHEN pb.phone IS NULL THEN ''
            WHEN pb.phone LIKE 'UNKNOWN_%' THEN ''
            WHEN pb.phone_norm_raw = '' THEN ''
            WHEN SUBSTR(pb.phone_norm_raw, 1, 2) = '98' AND LENGTH(pb.phone_norm_raw) = 12
                THEN '0' || SUBSTR(pb.phone_norm_raw, 3)
            WHEN SUBSTR(pb.phone_norm_raw, 1, 1) = '9' AND LENGTH(pb.phone_norm_raw) = 10
                THEN '0' || pb.phone_norm_raw
            WHEN SUBSTR(pb.phone_norm_raw, 1, 2) = '09' AND LENGTH(pb.phone_norm_raw) = 11
                THEN pb.phone_norm_raw
            ELSE ''
        END AS phone_norm
    FROM patient_base pb
),
appt_agg AS (
    SELECT
        a.patient_id,
        COUNT(*) AS visit_count,
        MIN(a.appointment_date) AS first_visit_date,
        MAX(a.appointment_date) AS last_visit_date,
        GROUP_CONCAT(DISTINCT
            CASE
                WHEN a.appointment_date_jalali IS NOT NULL AND TRIM(a.appointment_date_jalali) <> ''
                    THEN SUBSTR(TRIM(a.appointment_date_jalali), 1, 4)
                ELSE SUBSTR(a.appointment_date, 1, 4)
            END
        ) AS active_years
    FROM appointments a
    GROUP BY a.patient_id
),
phone_dup AS (
    SELECT
        phone_norm,
        COUNT(*) AS cnt
    FROM patient_clean
    WHERE phone_norm <> ''
    GROUP BY phone_norm
)
INSERT INTO identity_patient_features (
    patient_id,
    full_name,
    name_norm,
    name_token_sorted,
    primary_phone_norm,
    all_phones_norm,
    visit_count,
    first_visit_date,
    last_visit_date,
    active_years,
    household_phone_flag
)
SELECT
    pc.id AS patient_id,
    pc.name AS full_name,
    pc.name_norm_raw AS name_norm,
    pc.name_norm_raw AS name_token_sorted,
    pc.phone_norm AS primary_phone_norm,
    pc.phone_norm AS all_phones_norm,
    COALESCE(a.visit_count, 0) AS visit_count,
    COALESCE(a.first_visit_date, pc.first_visit_date) AS first_visit_date,
    COALESCE(a.last_visit_date, pc.first_visit_date) AS last_visit_date,
    COALESCE(a.active_years, SUBSTR(pc.first_visit_date, 1, 4)) AS active_years,
    CASE WHEN COALESCE(pd.cnt, 0) > 1 THEN 1 ELSE 0 END AS household_phone_flag
FROM patient_clean pc
LEFT JOIN appt_agg a
    ON a.patient_id = pc.id
LEFT JOIN phone_dup pd
    ON pd.phone_norm = pc.phone_norm;

COMMIT;
