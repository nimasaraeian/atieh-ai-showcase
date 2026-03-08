BEGIN;

DELETE FROM identity_patient_features;

WITH appt_agg AS (
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
    FROM (
        SELECT
            TRIM(
                REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                    REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                        LOWER(COALESCE(p.phone, '')),
                        ' ', ''), '-', ''), '(', ''), ')', ''), '+98', '0'),
                        '۰','0'), '۱','1'), '۲','2'), '۳','3'), '۴','4'),
                        '۵','5'), '۶','6'), '۷','7')
            ) AS phone_norm
        FROM patients p
    ) x
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
    p.id AS patient_id,
    p.name AS full_name,

    -- conservative name normalization
    TRIM(
        REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
            LOWER(COALESCE(p.name, '')),
            'ي', 'ی'),
            'ك', 'ک'),
            '  ', ' '),
            '  ', ' '),
            '  ', ' ')
    ) AS name_norm,

    -- phase 1: same as normalized name (token sorting later)
    TRIM(
        REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
            LOWER(COALESCE(p.name, '')),
            'ي', 'ی'),
            'ك', 'ک'),
            '  ', ' '),
            '  ', ' '),
            '  ', ' ')
    ) AS name_token_sorted,

    TRIM(
        REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
            REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                LOWER(COALESCE(p.phone, '')),
                ' ', ''), '-', ''), '(', ''), ')', ''), '+98', '0'),
                '۰','0'), '۱','1'), '۲','2'), '۳','3'), '۴','4'),
                '۵','5'), '۶','6'), '۷','7')
    ) AS primary_phone_norm,

    TRIM(
        REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
            REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                LOWER(COALESCE(p.phone, '')),
                ' ', ''), '-', ''), '(', ''), ')', ''), '+98', '0'),
                '۰','0'), '۱','1'), '۲','2'), '۳','3'), '۴','4'),
                '۵','5'), '۶','6'), '۷','7')
    ) AS all_phones_norm,

    COALESCE(a.visit_count, 0) AS visit_count,
    COALESCE(a.first_visit_date, p.first_visit_date) AS first_visit_date,
    COALESCE(a.last_visit_date, p.first_visit_date) AS last_visit_date,
    COALESCE(a.active_years, SUBSTR(p.first_visit_date, 1, 4)) AS active_years,

    CASE
        WHEN pd.cnt > 1 THEN 1
        ELSE 0
    END AS household_phone_flag

FROM patients p
LEFT JOIN appt_agg a
    ON a.patient_id = p.id
LEFT JOIN phone_dup pd
    ON pd.phone_norm = TRIM(
        REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
            REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                LOWER(COALESCE(p.phone, '')),
                ' ', ''), '-', ''), '(', ''), ')', ''), '+98', '0'),
                '۰','0'), '۱','1'), '۲','2'), '۳','3'), '۴','4'),
                '۵','5'), '۶','6'), '۷','7')
    );

COMMIT;
