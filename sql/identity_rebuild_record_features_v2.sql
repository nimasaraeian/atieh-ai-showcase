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
        MAX(CASE WHEN pc.patient_name_raw IS NOT NULL AND TRIM(pc.patient_name_raw) <> '' THEN pc.patient_name_raw END) AS payment_name_raw,
        MAX(CASE WHEN pc.phone_raw IS NOT NULL AND TRIM(pc.phone_raw) <> '' THEN pc.phone_raw END) AS phone_raw_any
    FROM payments_clean pc
    WHERE pc.record_no IS NOT NULL
      AND TRIM(pc.record_no) <> ''
    GROUP BY pc.record_no
),
record_base AS (
    SELECT
        pa.*,

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
        ) AS name_norm_raw,

        TRIM(
            REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
            REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                LOWER(COALESCE(pa.phone_raw_any, '')),
                ' ', ''), '-', ''), '(', ''), ')', ''), '+', ''),
                '۰','0'), '۱','1'), '۲','2'), '۳','3'), '۴','4'),
                '۵','5'), '۶','6'), '۷','7'), '۸','8'), '۹','9')
        ) AS phone_norm_raw
    FROM pay_agg pa
),
record_clean AS (
    SELECT
        rb.record_no,
        rb.payment_name_raw,
        rb.name_norm_raw,
        rb.payment_count,
        rb.first_payment_date,
        rb.last_payment_date,
        rb.active_years,

        CASE
            WHEN rb.phone_norm_raw = '' THEN ''
            WHEN SUBSTR(rb.phone_norm_raw, 1, 2) = '98' AND LENGTH(rb.phone_norm_raw) = 12
                THEN '0' || SUBSTR(rb.phone_norm_raw, 3)
            WHEN SUBSTR(rb.phone_norm_raw, 1, 1) = '9' AND LENGTH(rb.phone_norm_raw) = 10
                THEN '0' || rb.phone_norm_raw
            WHEN SUBSTR(rb.phone_norm_raw, 1, 2) = '09' AND LENGTH(rb.phone_norm_raw) = 11
                THEN rb.phone_norm_raw
            ELSE ''
        END AS phone_norm
    FROM record_base rb
),
phone_dup AS (
    SELECT
        phone_norm,
        COUNT(*) AS cnt
    FROM record_clean
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
    rc.record_no,
    rc.payment_name_raw,
    rc.name_norm_raw AS name_norm,
    rc.name_norm_raw AS name_token_sorted,
    rc.phone_norm AS matched_phone_norm,
    rc.payment_count,
    rc.first_payment_date,
    rc.last_payment_date,
    rc.active_years,
    CASE WHEN COALESCE(pd.cnt, 0) > 1 THEN 1 ELSE 0 END AS household_phone_flag
FROM record_clean rc
LEFT JOIN phone_dup pd
    ON pd.phone_norm = rc.phone_norm;

COMMIT;
