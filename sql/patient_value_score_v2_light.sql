DROP TABLE IF EXISTS patient_payment_fact_v2;
DROP TABLE IF EXISTS patient_value_score_v2;

CREATE TABLE patient_payment_fact_v2 AS
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
            WHEN pc.insurer_name_norm LIKE '%آزاد%' OR pc.insurer_name_norm LIKE '%نقد%' THEN 'آزاد'
            WHEN pc.insurer_name_norm LIKE '%تامين اجتماعي%' OR pc.insurer_name_norm LIKE '%تامین اجتماعی%' THEN 'تامین اجتماعی'
            WHEN pc.insurer_name_norm LIKE '%جانبازان نیروهای مسلح%' THEN 'جانبازان نیروهای مسلح'
            WHEN pc.insurer_name_norm LIKE '%نیروهای مسلح%' THEN 'نیروهای مسلح'
            WHEN pc.insurer_name_norm LIKE '%بانک ملت%' THEN 'بانک ملت'
            WHEN pc.insurer_name_norm LIKE '%بانک سپه%' OR pc.insurer_name_norm = 'سپه' THEN 'بانک سپه'
            WHEN pc.insurer_name_norm LIKE '%بانک ملی%' OR pc.insurer_name_norm LIKE '%ملی بازنشسته%' THEN 'بانک ملی'
            WHEN pc.insurer_name_norm LIKE '%کشاورزی%' THEN 'بانک کشاورزی'
            WHEN pc.insurer_name_norm LIKE '%شرکت نفت%' THEN 'شرکت نفت'
            WHEN pc.insurer_name_norm LIKE '%اسيا%' OR pc.insurer_name_norm LIKE '%آسیا%' OR pc.insurer_name_norm LIKE '%اسیا%' THEN 'آسیا'
            WHEN pc.insurer_name_norm = 'دی' OR pc.insurer_name_norm LIKE '%بیمه دی%' OR pc.insurer_name_norm LIKE '%دي%' THEN 'دی'
            WHEN pc.insurer_name_norm LIKE '%البرز%' THEN 'البرز'
            WHEN pc.insurer_name_norm LIKE '%سينا%' OR pc.insurer_name_norm LIKE '%سینا%' THEN 'سینا'
            WHEN pc.insurer_name_norm LIKE '%كوثر%' OR pc.insurer_name_norm LIKE '%کوثر%' THEN 'کوثر'
            WHEN lower(pc.insurer_name_norm) LIKE '%sos%' THEN 'sos'
            WHEN pc.insurer_name_norm LIKE '%پارسيان%' OR pc.insurer_name_norm LIKE '%پارسیان%' THEN 'پارسیان'
            WHEN pc.insurer_name_norm LIKE '%پاسارگاد%' THEN 'پاسارگاد'
            WHEN pc.insurer_name_norm LIKE '%صداوسيما%' OR pc.insurer_name_norm LIKE '%صداوسیما%' THEN 'صداوسیما'
            WHEN pc.insurer_name_norm LIKE '%کارآفرین%' OR pc.insurer_name_norm LIKE '%کار افرین%' THEN 'کارآفرین'
            WHEN pc.insurer_name_norm LIKE '%ايران%' OR pc.insurer_name_norm LIKE '%ایران%' THEN 'ایران'
            WHEN pc.insurer_name_norm LIKE '%معلم%' THEN 'معلم'
            WHEN pc.insurer_name_norm LIKE '%آتیه سازان حافظ%' THEN 'آتیه سازان حافظ'
            WHEN pc.insurer_name_norm LIKE '%دانا%' THEN 'دانا'
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
    COALESCE(ir.insurer_weight,
        CASE
            WHEN b.payer_source_norm = 'cash' THEN 20
            WHEN b.payer_source_norm = 'insurance' THEN 60
            ELSE 40
        END
    ) AS insurer_weight
FROM base b
LEFT JOIN insurance_reference ir
  ON ir.canonical_name = b.insurer_canonical
;

CREATE INDEX IF NOT EXISTS idx_ppf2_patient_id ON patient_payment_fact_v2(patient_id);

CREATE TABLE patient_value_score_v2 AS
WITH patient_agg AS (
    SELECT
        p.id AS patient_id,
        p.name,
        COUNT(DISTINCT f.stg_payment_id) AS txn_count,
        ROUND(COALESCE(SUM(f.net_received_rial),0) / 10.0, 2) AS lifetime_net_received_toman,
        SUM(CASE WHEN f.payer_source_norm = 'cash' THEN 1 ELSE 0 END) AS cash_txn_count,
        SUM(CASE WHEN f.payer_source_norm = 'insurance' THEN 1 ELSE 0 END) AS insurance_txn_count,
        ROUND(COALESCE(AVG(CASE
            WHEN f.insurer_canonical IS NOT NULL
             AND f.insurer_canonical <> 'آزاد'
             AND f.payer_source_norm = 'insurance'
            THEN f.insurer_weight END),0),2) AS avg_insurer_weight,
        MAX(f.jalali_year) AS last_jalali_year
    FROM patients p
    LEFT JOIN patient_payment_fact_v2 f
      ON f.patient_id = p.id
    GROUP BY p.id, p.name
),
dominant_insurer AS (
    SELECT patient_id, insurer_canonical AS dominant_insurer
    FROM (
        SELECT
            f.patient_id,
            f.insurer_canonical,
            COUNT(*) AS c,
            ROW_NUMBER() OVER (
                PARTITION BY f.patient_id
                ORDER BY COUNT(*) DESC, f.insurer_canonical
            ) AS rn
        FROM patient_payment_fact_v2 f
        WHERE f.insurer_canonical IS NOT NULL
          AND f.insurer_canonical <> 'آزاد'
          AND f.payer_source_norm = 'insurance'
        GROUP BY f.patient_id, f.insurer_canonical
    ) x
    WHERE rn = 1
)
SELECT
    a.patient_id,
    a.name,
    a.txn_count,
    a.lifetime_net_received_toman,
    d.dominant_insurer,
    a.avg_insurer_weight,
    a.last_jalali_year,
    ROUND(
        (CASE
            WHEN a.txn_count >= 80 THEN 100
            WHEN a.txn_count >= 40 THEN 90
            WHEN a.txn_count >= 20 THEN 78
            WHEN a.txn_count >= 10 THEN 65
            WHEN a.txn_count >= 5 THEN 50
            WHEN a.txn_count >= 1 THEN 30
            ELSE 0
        END) * 0.28
        +
        (CASE
            WHEN a.lifetime_net_received_toman >= 30000000 THEN 100
            WHEN a.lifetime_net_received_toman >= 15000000 THEN 88
            WHEN a.lifetime_net_received_toman >= 7000000 THEN 75
            WHEN a.lifetime_net_received_toman >= 3000000 THEN 60
            WHEN a.lifetime_net_received_toman >= 1000000 THEN 45
            WHEN a.lifetime_net_received_toman > 0 THEN 25
            ELSE 0
        END) * 0.32
        +
        (CASE
            WHEN a.last_jalali_year >= 1404 THEN 100
            WHEN a.last_jalali_year = 1403 THEN 80
            WHEN a.last_jalali_year = 1402 THEN 60
            WHEN a.last_jalali_year = 1401 THEN 40
            WHEN a.last_jalali_year IS NOT NULL THEN 20
            ELSE 0
        END) * 0.22
        +
        (CASE
            WHEN a.insurance_txn_count > 0 THEN CAST(COALESCE(a.avg_insurer_weight,0) AS INTEGER)
            WHEN a.cash_txn_count > 0 THEN 20
            ELSE 0
        END) * 0.18
    , 2) AS patient_value_score
FROM patient_agg a
LEFT JOIN dominant_insurer d
  ON d.patient_id = a.patient_id
;

CREATE INDEX IF NOT EXISTS idx_pvs2_patient_id ON patient_value_score_v2(patient_id);
