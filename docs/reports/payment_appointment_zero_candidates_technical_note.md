# Payment → Appointment Zero-Candidate Issue – Technical Note

## Observation

The identity resolution pipeline reports **zero** candidates for the pair **payment ↔ appointment** (rule B7: phone exact match).

## How B7 is generated

1. **Source tables:** `identity_normalized_payments` (mobile_primary_norm) and `identity_normalized_appointments` (phone_primary_norm).
2. **Logic:** For each payment row with a non-null `mobile_primary_norm`, look up appointment rows with the same `phone_primary_norm`; for each match insert a candidate (B7_payment_appointment_phone_exact).
3. **Result:** Zero candidates mean no (payment_phone, appointment_phone) pair is equal.

## Possible causes

| Cause | Description |
|-------|-------------|
| **Empty appointment side** | `appointments_unified_staging` or `identity_normalized_appointments` has no rows (e.g. appointment import not run, or no files found). |
| **No phones on appointments** | Appointment Excel columns for phone were missing or not mapped; all `phone_primary_norm` are NULL. |
| **No overlap** | Payments and appointments use different phone populations (e.g. different years/sources) so the same normalized phone never appears on both sides. |
| **Normalization mismatch** | Payments and appointments use the same helper, but one side was populated from a source that stores phones in a way that normalizes to a different string (e.g. leading zeros, spaces). Unlikely if both use `normalize_phone_primary_and_all`. |

## Diagnostic queries

Run against the same DB used for identity resolution:

```sql
-- 1) Row counts
SELECT 'payments_unified_staging' AS tbl, COUNT(*) AS n FROM payments_unified_staging
UNION ALL
SELECT 'identity_normalized_payments', COUNT(*) FROM identity_normalized_payments
UNION ALL
SELECT 'appointments_unified_staging', COUNT(*) FROM appointments_unified_staging
UNION ALL
SELECT 'identity_normalized_appointments', COUNT(*) FROM identity_normalized_appointments;

-- 2) Phones present
SELECT 'payments with mobile_primary_norm', COUNT(*) FROM identity_normalized_payments WHERE mobile_primary_norm IS NOT NULL AND TRIM(mobile_primary_norm) <> ''
UNION ALL
SELECT 'appointments with phone_primary_norm', COUNT(*) FROM identity_normalized_appointments WHERE phone_primary_norm IS NOT NULL AND TRIM(phone_primary_norm) <> '';

-- 3) Overlap: count of payment phones that appear in appointments
SELECT COUNT(DISTINCT p.mobile_primary_norm) AS payment_phones_in_appointments
FROM identity_normalized_payments p
WHERE p.mobile_primary_norm IS NOT NULL AND TRIM(p.mobile_primary_norm) <> ''
  AND EXISTS (
    SELECT 1 FROM identity_normalized_appointments a
    WHERE a.phone_primary_norm = p.mobile_primary_norm
  );
```

- If (1) shows zero for appointment tables → run `import_appointments_unified.py` and ensure Excel paths exist.
- If (2) shows zero for appointments with phone → fix appointment column mapping or source data.
- If (1)–(2) are non-zero but (3) is zero → no overlap; investigate whether appointment files cover the same patients/years as payment files.

## Next steps

1. Run the diagnostics above and record the counts.
2. If appointment staging/normalized is empty: run the full appointment import and normalization, then re-run candidate generation.
3. If appointments have no phones: confirm header mapping in `import_appointments_unified.py` (PHONE_HEADERS) and that the Excel files actually contain a phone column.
4. If overlap is zero despite both sides having phones: consider reporting sample `mobile_primary_norm` (payments) and `phone_primary_norm` (appointments) to verify format alignment; check for year/source coverage differences.

---

*This note is for investigation only. No schema or data changes are required to run these diagnostics.*
