# CRM Code → Patient Link Report

Bridge between CRM financial identity (crm_patient_code) and patients table.
Linking uses: patient_name_key (exact), phone_primary_norm / phone_all_norm.

## Outputs

| Metric | Value |
|--------|-------|
| CRM codes linked to patients (promoted) | 32,595 |
| Patient entities recovered (distinct patient_id in promoted) | 27,661 |
| Ambiguity rows (multiple patients per code) | 126,500 |
| Ambiguous CRM codes (distinct) | 17,257 |
| Payment rows with extracted code (denominator) | 876,054 |
| Payment rows linked to promoted patients | 360,647 |
| Coverage (financial rows linked to patient entities) | 41.17% |

## Confidence tiers

- **high:** 0 links
- **medium:** 32,595 links
- **low:** 0 links
