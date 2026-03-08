BEGIN;

DELETE FROM identity_record_features;

WITH pay_agg AS (
    SELECT
        pc.record_no,
        COUNT(*) AS payment_count,
        MIN(pc.appointment_date_raw) AS first_payment_date,
        MAX(pc.appointment_date_raw) AS last_payment_date,
        GROUP_CONCAT(DISTINCT
            CASE
                WHEN pc.appointment_date_raw IS NOT NULL AND TRIM(pc.appointment_date_raw) <> ''
                    THEN SUBSTR(TRIM(pc.appointment_date_raw), 1, 4)
                ELSE NULL
            END
        ) AS active_years,

        MAX(
            CASE
                WHEN pc.patient_name_raw IS NOT NULL AND TRIM(pc.patient_name_raw) <> ''
                    THEN pc.patient_name_raw
                ELSE NULL
            END
        ) AS payment_name_raw,

        MAX(
            CASE
                WHEN pc.phone_raw IS NOT NULL AND TRIM(pc.phone_raw) <> ''
                    THEN pc.phone_raw
                ELSE NULL
            END
        ) AS phone_raw_any
    FROM payments_clean pc
    WHERE pc.record_no IS NOT NULL
      AND TRIM(pc.record_no) <> ''
    GROUP BY pc.record_no
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
                        LOWER(COALESCE(phone_raw_any, '')),
                        ' ', ''), '-', ''), '(', ''), ')', ''), '+98', '0'),
                        '۰','0'), '۱','1'), '۲','2'), '۳','3'), '۴','4'),
                        '۵','5'), '۶','6'), '۷','7')
            ) AS phone_norm
        FROM pay_agg
    ) x
    WHERE phone_norm <> ''
    GROUP BY phone_norm
)
INSERT INTO identity_record_features (
    record_no,
    payment_name_raw,
    name_norm,
    name_token_sorted,
    matched_phone_norm,
    payment_count,
    first_payment_date,
    last_payment_date,
    active_years,
    household_phone_flag
)
SELECT
    pa.record_no,
    pa.payment_name_raw,

    -- remove suffix like "(101674)" conservatively if present
    TRIM(
        REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
            LOWER(
                CASE
                    WHEN INSTR(COALESCE(pa.payment_name_raw, ''), '(') > 0
                        THEN SUBSTR(pa.payment_name_raw, 1, INSTR(pa.payment_name_raw, '(') - 1)
                    ELSE COALESCE(pa.payment_name_raw, '')
                END
            ),
            'ي', 'ی'),
            'ك', 'ک'),
            '  ', ' '),
            '  ', ' '),
            '  ', ' ')
    ) AS name_norm,

    TRIM(
        REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
            LOWER(
                CASE
                    WHEN INSTR(COALESCE(pa.payment_name_raw, ''), '(') > 0
                        THEN SUBSTR(pa.payment_name_raw, 1, INSTR(pa.payment_name_raw, '(') - 1)
                    ELSE COALESCE(pa.payment_name_raw, '')
                END
            ),
            'ي', 'ی'),
            'ك', 'ک'),
            '  ', ' '),
            '  ', ' '),
            '  ', ' ')
    ) AS name_token_sorted,

    TRIM(
        REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
            REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                LOWER(COALESCE(pa.phone_raw_any, '')),
                ' ', ''), '-', ''), '(', ''), ')', ''), '+98', '0'),
                '۰','0'), '۱','1'), '۲','2'), '۳','3'), '۴','4'),
                '۵','5'), '۶','6'), '۷','7')
    ) AS matched_phone_norm,

    pa.payment_count,
    pa.first_payment_date,
    pa.last_payment_date,
    pa.active_years,

    CASE
        WHEN pd.cnt > 1 THEN 1
        ELSE 0
    END AS household_phone_flag

FROM pay_agg pa
LEFT JOIN phone_dup pd
    ON pd.phone_norm = TRIM(
        REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
            REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                LOWER(COALESCE(pa.phone_raw_any, '')),
                ' ', ''), '-', ''), '(', ''), ')', ''), '+98', '0'),
                '۰','0'), '۱','1'), '۲','2'), '۳','3'), '۴','4'),
                '۵','5'), '۶','6'), '۷','7')
    );

COMMIT;
