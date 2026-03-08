-- Migration 003: Payment Type Normalization
-- Adds payment_type_raw (original text) and payment_type_norm (canonical value) to appointments.
-- Backfills all existing rows and updates the legacy payment_type to the canonical value.
--
-- Canonical values: 'cash' | 'insurance' | 'card' | 'transfer' | 'installment' | 'unknown'

-- ── Step 1: Add new columns ────────────────────────────────────────────────
ALTER TABLE appointments ADD COLUMN payment_type_raw  TEXT;
ALTER TABLE appointments ADD COLUMN payment_type_norm TEXT;

-- ── Step 2: Backfill payment_type_raw ─────────────────────────────────────
-- For rows where the importer always wrote 'CASH' but the actual payment was
-- insurance (detectable via raw_text_insurance), preserve the insurance org name.
-- For everything else keep the existing payment_type value.
UPDATE appointments
SET payment_type_raw = CASE
        WHEN raw_text_insurance IS NOT NULL
             AND raw_text_insurance != ''
             AND UPPER(payment_type) = 'CASH'
        THEN raw_text_insurance          -- the insurance org/company name
        ELSE payment_type                -- e.g. 'CASH', 'INSURANCE_5', …
    END
WHERE payment_type_raw IS NULL;

-- ── Step 3: Backfill payment_type_norm ────────────────────────────────────
UPDATE appointments
SET payment_type_norm = CASE
        -- INSURANCE_<n> legacy enum values → insurance
        WHEN UPPER(payment_type_raw) LIKE 'INSURANCE_%'          THEN 'insurance'
        -- free-text that contains insurance keyword variants
        WHEN UPPER(payment_type_raw) LIKE '%INSURANCE%'           THEN 'insurance'
        WHEN payment_type_raw        LIKE '%بیمه%'                THEN 'insurance'
        WHEN UPPER(payment_type_raw) LIKE '%SIGORTA%'             THEN 'insurance'
        -- rows where raw_text_insurance was non-empty (i.e. payment_type_raw IS the org name)
        WHEN raw_text_insurance IS NOT NULL
             AND raw_text_insurance != ''
             AND payment_type_raw = raw_text_insurance            THEN 'insurance'
        -- cash variants
        WHEN UPPER(payment_type_raw) = 'CASH'                     THEN 'cash'
        WHEN payment_type_raw IN ('cash','نقد','نقدی','NAKIT','NAKİT') THEN 'cash'
        -- card / POS
        WHEN UPPER(payment_type_raw) LIKE '%CARD%'
          OR UPPER(payment_type_raw) LIKE '%POS%'
          OR UPPER(payment_type_raw) LIKE '%KART%'
          OR UPPER(payment_type_raw) LIKE '%KREDI%'               THEN 'card'
        -- bank transfer / wire / EFT
        WHEN UPPER(payment_type_raw) LIKE '%TRANSFER%'
          OR UPPER(payment_type_raw) LIKE '%HAVALE%'
          OR UPPER(payment_type_raw) LIKE '%EFT%'
          OR UPPER(payment_type_raw) LIKE '%WIRE%'                THEN 'transfer'
        -- instalment
        WHEN UPPER(payment_type_raw) LIKE '%INSTALLMENT%'
          OR UPPER(payment_type_raw) LIKE '%TAKSIT%'
          OR payment_type_raw        LIKE '%قسط%'                 THEN 'installment'
        ELSE 'unknown'
    END
WHERE payment_type_norm IS NULL;

-- ── Step 4: Write normalised value back to legacy column ──────────────────
-- APIs and analytics read payment_type; point it to the canonical value.
UPDATE appointments
SET payment_type = payment_type_norm
WHERE payment_type_norm IS NOT NULL;

-- ── Step 5: Index for analytics queries ───────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_appointments_payment_type_norm
    ON appointments(payment_type_norm);
