DROP TABLE IF EXISTS insurer_score_map;
DROP TABLE IF EXISTS patient_payment_fact_v1;
DROP TABLE IF EXISTS patient_value_score_v1;

CREATE TABLE insurer_score_map (
    insurer_name TEXT PRIMARY KEY,
    insurer_score INTEGER NOT NULL
);

INSERT INTO insurer_score_map (insurer_name, insurer_score) VALUES
('تامین اجتماعی', 70),
('نیروهای مسلح', 85),
('جانبازان نیروهای مسلح', 90),
('شرکت نفت', 88),
('بانک ملت', 82),
('سپه', 82),
('کشاورزی', 78),
('البرز', 72),
('آسیا', 72),
('سینا', 72),
('بیمه دی', 75),
('پارسیان', 74),
('پاسارگاد', 74),
('معلم', 70),
('کوثر', 73),
('آتیه سازان حافظ', 68),
('ایران', 73),
('دانا', 72),
('sos', 76),
('وام', 40),
('آزاد', 20);

CREATE TABLE patient_payment_fact_v1 AS
WITH base AS (
    SELECT
        pc.patient_id,
        pc.stg_payment_id,
        COALESCE(pc.net_received, 0) AS net_received_rial,
        COALESCE(pc.amount_patient, 0) AS amount_patient_rial,
        COALESCE(pc.amount_insurer, 0) AS amount_insurer_rial,
        pc.payer_source_norm,
        pc.appointment_date_iso,
        pc.appointment_date_raw,
        CASE
            WHEN pc.insurer_name_norm IS NULL OR trim(pc.insurer_name_norm) = '' THEN NULL
            WHEN pc.insurer_name_norm LIKE '%آزاد%' THEN 'آزاد'
            WHEN pc.insurer_name_norm LIKE '%تامین اجتماعی%' THEN 'تامین اجتماعی'
            WHEN pc.insurer_name_norm LIKE '%جانبازان نیروهای مسلح%' THEN 'جانبازان نیروهای مسلح'
            WHEN pc.insurer_name_norm LIKE '%نیروهای مسلح%' THEN 'نیروهای مسلح'
            WHEN pc.insurer_name_norm LIKE '%شرکت نفت%' THEN 'شرکت نفت'
            WHEN pc.insurer_name_norm LIKE '%بانک ملت%' THEN 'بانک ملت'
            WHEN pc.insurer_name_norm LIKE '%سپه%' THEN 'سپه'
            WHEN pc.insurer_name_norm LIKE '%کشاورزی%' THEN 'کشاورزی'
            WHEN pc.insurer_name_norm LIKE '%البرز%' THEN 'البرز'
            WHEN pc.insurer_name_norm LIKE '%اسيا%' OR pc.insurer_name_norm LIKE '%آسیا%' OR pc.insurer_name_norm LIKE '%اسیا%' THEN 'آسیا'
            WHEN pc.insurer_name_norm LIKE '%سينا%' OR pc.insurer_name_norm LIKE '%سینا%' THEN 'سینا'
            WHEN pc.insurer_name_norm LIKE '%بیمه دی%' OR pc.insurer_name_norm LIKE '%دي%' THEN 'بیمه دی'
            WHEN pc.insurer_name_norm LIKE '%پارسيان%' OR pc.insurer_name_norm LIKE '%پارسیان%' THEN 'پارسیان'
            WHEN pc.insurer_name_norm LIKE '%پاسارگاد%' THEN 'پاسارگاد'
            WHEN pc.insurer_name_norm LIKE '%معلم%' THEN 'معلم'
            WHEN pc.insurer_name_norm LIKE '%كوثر%' OR pc.insurer_name_norm LIKE '%کوثر%' THEN 'کوثر'
            WHEN pc.insurer_name_norm LIKE '%آتیه سازان حافظ%' THEN 'آتیه سازان حافظ'
            WHEN pc.insurer_name_norm LIKE '%ايران%' OR pc.insurer_name_norm LIKE '%ایران%' THEN 'ایران'
            WHEN pc.insurer_name_norm LIKE '%دانا%' THEN 'دانا'
            WHEN lower(pc.insurer_name_norm) LIKE '%sos%' THEN 'sos'
            WHEN pc.insurer_name_norm LIKE '%وام%' THEN 'وام'
            ELSE pc.insurer_name_norm
        END AS insurer_canonical,
        CASE
            WHEN substr(COALESCE(pc.appointment_date_raw,''),1,4) GLOB '[0-9][0-9][0-9][0-9]'
            THEN CAST(substr(pc.appointment_date_raw,1,4) AS INTEGER)
            ELSE NULL
        END AS jalali_year
    FROM payments_clean pc
    WHERE pc.patient_id IS NOT NULL
)
SELECT
    b.*,
    COALESCE(m.insurer_score, CASE WHEN b.payer_source_norm = 'cash' THEN 20 ELSE 55 END) AS insurer_score
FROM base b
LEFT JOIN insurer_score_map m
  ON m.insurer_name = b.insurer_canonical
;

CREATE INDEX IF NOT EXISTS idx_ppf1_patient_id ON patient_payment_fact_v1(patient_id);
CREATE INDEX IF NOT EXISTS idx_ppf1_insurer ON patient_payment_fact_v1(insurer_canonical);

CREATE TABLE patient_value_score_v1 AS
WITH patient_agg AS (
    SELECT
        p.id AS patient_id,
        p.name,
        p.phone,

        COUNT(DISTINCT f.stg_payment_id) AS txn_count,
        ROUND(COALESCE(SUM(f.net_received_rial),0) / 10.0, 2) AS lifetime_net_received_toman,
        ROUND(COALESCE(SUM(f.amount_patient_rial),0) / 10.0, 2) AS lifetime_amount_patient_toman,
        ROUND(COALESCE(SUM(f.amount_insurer_rial),0) / 10.0, 2) AS lifetime_amount_insurer_toman,
        ROUND(COALESCE(AVG(f.net_received_rial),0) / 10.0, 2) AS avg_net_received_toman,

        SUM(CASE WHEN f.payer_source_norm = 'cash' THEN 1 ELSE 0 END) AS cash_txn_count,
        SUM(CASE WHEN f.payer_source_norm = 'insurance' THEN 1 ELSE 0 END) AS insurance_txn_count,

        COUNT(DISTINCT CASE
            WHEN f.insurer_canonical IS NOT NULL
             AND f.insurer_canonical <> 'آزاد'
             AND f.payer_source_norm = 'insurance'
            THEN f.insurer_canonical END
        ) AS insurer_count,

        ROUND(COALESCE(AVG(CASE
            WHEN f.insurer_canonical IS NOT NULL
             AND f.insurer_canonical <> 'آزاد'
             AND f.payer_source_norm = 'insurance'
            THEN f.insurer_score END),0),2) AS avg_insurer_score,

        MAX(COALESCE(f.appointment_date_iso, f.appointment_date_raw)) AS last_payment_date_raw,
        MAX(f.jalali_year) AS last_jalali_year
    FROM patients p
    LEFT JOIN patient_payment_fact_v1 f
      ON f.patient_id = p.id
    GROUP BY p.id, p.name, p.phone
),
dominant_insurer AS (
    SELECT
        x.patient_id,
        x.insurer_canonical AS dominant_insurer
    FROM (
        SELECT
            f.patient_id,
            f.insurer_canonical,
            COUNT(*) AS c,
            ROW_NUMBER() OVER (
                PARTITION BY f.patient_id
                ORDER BY COUNT(*) DESC, f.insurer_canonical
            ) AS rn
        FROM patient_payment_fact_v1 f
        WHERE f.insurer_canonical IS NOT NULL
          AND f.insurer_canonical <> 'آزاد'
          AND f.payer_source_norm = 'insurance'
        GROUP BY f.patient_id, f.insurer_canonical
    ) x
    WHERE x.rn = 1
)
SELECT
    a.patient_id,
    a.name,
    a.phone,
    a.txn_count,
    a.lifetime_net_received_toman,
    a.lifetime_amount_patient_toman,
    a.lifetime_amount_insurer_toman,
    a.avg_net_received_toman,
    a.cash_txn_count,
    a.insurance_txn_count,
    a.insurer_count,
    a.avg_insurer_score,
    d.dominant_insurer,
    a.last_payment_date_raw,
    a.last_jalali_year,

    CASE
        WHEN a.txn_count >= 15 THEN 100
        WHEN a.txn_count >= 10 THEN 85
        WHEN a.txn_count >= 6 THEN 70
        WHEN a.txn_count >= 3 THEN 50
        WHEN a.txn_count >= 1 THEN 25
        ELSE 0
    END AS txn_score,

    CASE
        WHEN a.lifetime_net_received_toman >= 10000000 THEN 100
        WHEN a.lifetime_net_received_toman >= 5000000 THEN 85
        WHEN a.lifetime_net_received_toman >= 2000000 THEN 70
        WHEN a.lifetime_net_received_toman >= 500000 THEN 50
        WHEN a.lifetime_net_received_toman > 0 THEN 25
        ELSE 0
    END AS value_score_component,

    CASE
        WHEN a.last_jalali_year >= 1404 THEN 100
        WHEN a.last_jalali_year = 1403 THEN 80
        WHEN a.last_jalali_year = 1402 THEN 60
        WHEN a.last_jalali_year = 1401 THEN 40
        WHEN a.last_jalali_year IS NOT NULL THEN 20
        ELSE 0
    END AS recency_score,

    CASE
        WHEN a.insurance_txn_count > 0 THEN CAST(COALESCE(a.avg_insurer_score,0) AS INTEGER)
        WHEN a.cash_txn_count > 0 THEN 20
        ELSE 0
    END AS insurance_score_component,

    ROUND(
        (
            CASE
                WHEN a.txn_count >= 15 THEN 100
                WHEN a.txn_count >= 10 THEN 85
                WHEN a.txn_count >= 6 THEN 70
                WHEN a.txn_count >= 3 THEN 50
                WHEN a.txn_count >= 1 THEN 25
                ELSE 0
            END
        ) * 0.30
        +
        (
            CASE
                WHEN a.lifetime_net_received_toman >= 10000000 THEN 100
                WHEN a.lifetime_net_received_toman >= 5000000 THEN 85
                WHEN a.lifetime_net_received_toman >= 2000000 THEN 70
                WHEN a.lifetime_net_received_toman >= 500000 THEN 50
                WHEN a.lifetime_net_received_toman > 0 THEN 25
                ELSE 0
            END
        ) * 0.35
        +
        (
            CASE
                WHEN a.last_jalali_year >= 1404 THEN 100
                WHEN a.last_jalali_year = 1403 THEN 80
                WHEN a.last_jalali_year = 1402 THEN 60
                WHEN a.last_jalali_year = 1401 THEN 40
                WHEN a.last_jalali_year IS NOT NULL THEN 20
                ELSE 0
            END
        ) * 0.20
        +
        (
            CASE
                WHEN a.insurance_txn_count > 0 THEN CAST(COALESCE(a.avg_insurer_score,0) AS INTEGER)
                WHEN a.cash_txn_count > 0 THEN 20
                ELSE 0
            END
        ) * 0.15
    , 2) AS patient_value_score,

    CASE
        WHEN ROUND(
            (
                CASE
                    WHEN a.txn_count >= 15 THEN 100
                    WHEN a.txn_count >= 10 THEN 85
                    WHEN a.txn_count >= 6 THEN 70
                    WHEN a.txn_count >= 3 THEN 50
                    WHEN a.txn_count >= 1 THEN 25
                    ELSE 0
                END
            ) * 0.30
            +
            (
                CASE
                    WHEN a.lifetime_net_received_toman >= 10000000 THEN 100
                    WHEN a.lifetime_net_received_toman >= 5000000 THEN 85
                    WHEN a.lifetime_net_received_toman >= 2000000 THEN 70
                    WHEN a.lifetime_net_received_toman >= 500000 THEN 50
                    WHEN a.lifetime_net_received_toman > 0 THEN 25
                    ELSE 0
                END
            ) * 0.35
            +
            (
                CASE
                    WHEN a.last_jalali_year >= 1404 THEN 100
                    WHEN a.last_jalali_year = 1403 THEN 80
                    WHEN a.last_jalali_year = 1402 THEN 60
                    WHEN a.last_jalali_year = 1401 THEN 40
                    WHEN a.last_jalali_year IS NOT NULL THEN 20
                    ELSE 0
                END
            ) * 0.20
            +
            (
                CASE
                    WHEN a.insurance_txn_count > 0 THEN CAST(COALESCE(a.avg_insurer_score,0) AS INTEGER)
                    WHEN a.cash_txn_count > 0 THEN 20
                    ELSE 0
                END
            ) * 0.15
        , 2) >= 85 THEN 'VIP'
        WHEN ROUND(
            (
                CASE
                    WHEN a.txn_count >= 15 THEN 100
                    WHEN a.txn_count >= 10 THEN 85
                    WHEN a.txn_count >= 6 THEN 70
                    WHEN a.txn_count >= 3 THEN 50
                    WHEN a.txn_count >= 1 THEN 25
                    ELSE 0
                END
            ) * 0.30
            +
            (
                CASE
                    WHEN a.lifetime_net_received_toman >= 10000000 THEN 100
                    WHEN a.lifetime_net_received_toman >= 5000000 THEN 85
                    WHEN a.lifetime_net_received_toman >= 2000000 THEN 70
                    WHEN a.lifetime_net_received_toman >= 500000 THEN 50
                    WHEN a.lifetime_net_received_toman > 0 THEN 25
                    ELSE 0
                END
            ) * 0.35
            +
            (
                CASE
                    WHEN a.last_jalali_year >= 1404 THEN 100
                    WHEN a.last_jalali_year = 1403 THEN 80
                    WHEN a.last_jalali_year = 1402 THEN 60
                    WHEN a.last_jalali_year = 1401 THEN 40
                    WHEN a.last_jalali_year IS NOT NULL THEN 20
                    ELSE 0
                END
            ) * 0.20
            +
            (
                CASE
                    WHEN a.insurance_txn_count > 0 THEN CAST(COALESCE(a.avg_insurer_score,0) AS INTEGER)
                    WHEN a.cash_txn_count > 0 THEN 20
                    ELSE 0
                END
            ) * 0.15
        , 2) >= 70 THEN 'HIGH'
        WHEN ROUND(
            (
                CASE
                    WHEN a.txn_count >= 15 THEN 100
                    WHEN a.txn_count >= 10 THEN 85
                    WHEN a.txn_count >= 6 THEN 70
                    WHEN a.txn_count >= 3 THEN 50
                    WHEN a.txn_count >= 1 THEN 25
                    ELSE 0
                END
            ) * 0.30
            +
            (
                CASE
                    WHEN a.lifetime_net_received_toman >= 10000000 THEN 100
                    WHEN a.lifetime_net_received_toman >= 5000000 THEN 85
                    WHEN a.lifetime_net_received_toman >= 2000000 THEN 70
                    WHEN a.lifetime_net_received_toman >= 500000 THEN 50
                    WHEN a.lifetime_net_received_toman > 0 THEN 25
                    ELSE 0
                END
            ) * 0.35
            +
            (
                CASE
                    WHEN a.last_jalali_year >= 1404 THEN 100
                    WHEN a.last_jalali_year = 1403 THEN 80
                    WHEN a.last_jalali_year = 1402 THEN 60
                    WHEN a.last_jalali_year = 1401 THEN 40
                    WHEN a.last_jalali_year IS NOT NULL THEN 20
                    ELSE 0
                END
            ) * 0.20
            +
            (
                CASE
                    WHEN a.insurance_txn_count > 0 THEN CAST(COALESCE(a.avg_insurer_score,0) AS INTEGER)
                    WHEN a.cash_txn_count > 0 THEN 20
                    ELSE 0
                END
            ) * 0.15
        , 2) >= 50 THEN 'MEDIUM'
        WHEN a.txn_count > 0 THEN 'LOW'
        ELSE 'NONE'
    END AS financial_tier,

    CASE
        WHEN a.txn_count = 0 THEN 'NO_PAYMENT_HISTORY'
        WHEN a.last_jalali_year IS NULL THEN 'CHECK_HISTORY'
        WHEN a.last_jalali_year <= 1401 AND a.txn_count >= 3 THEN 'STRONG_REACTIVATION'
        WHEN a.last_jalali_year <= 1402 AND a.txn_count >= 2 THEN 'REACTIVATION'
        WHEN a.last_jalali_year >= 1404 AND a.txn_count >= 8 THEN 'LOYAL_ACTIVE'
        WHEN a.last_jalali_year >= 1404 THEN 'ACTIVE'
        ELSE 'MEDIUM_REVIEW'
    END AS followup_type,

    CASE
        WHEN a.txn_count = 0 THEN 0
        WHEN a.last_jalali_year <= 1401 AND a.txn_count >= 3 THEN 90
        WHEN a.last_jalali_year <= 1402 AND a.txn_count >= 2 THEN 75
        WHEN a.last_jalali_year >= 1404 AND a.txn_count >= 8 THEN 95
        WHEN a.last_jalali_year >= 1404 THEN 70
        ELSE 50
    END AS reactivation_score

FROM patient_agg a
LEFT JOIN dominant_insurer d
  ON d.patient_id = a.patient_id
;

CREATE INDEX IF NOT EXISTS idx_pvs1_patient_id ON patient_value_score_v1(patient_id);
CREATE INDEX IF NOT EXISTS idx_pvs1_tier ON patient_value_score_v1(financial_tier);
CREATE INDEX IF NOT EXISTS idx_pvs1_score ON patient_value_score_v1(patient_value_score);
