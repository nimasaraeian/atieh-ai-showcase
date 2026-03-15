# Patient Identity Resolution Phase 2 – Safe Promotion Report

## Summary

- **Total promoted safe matches:** 105747
- **Criteria:** `confidence_tier = 'A'` and `match_status != 'ambiguous'`
- **Rules promoted:** A2 (primary anchor), A3, B1 only

## Promoted matches by rule

| candidate_rule | promotion_reason | count |
|----------------|------------------|-------|
| A2_phone_exact_name_exact | primary_anchor | 105082 |
| B1_phone_exact_only | B1_phone_exact_only | 348 |
| A3_phone_exact_name_high_sim | A3_phone_exact_name_high_sim | 317 |

## Promoted matches by pair type

| left_source_type | right_source_type | count |
|------------------|-------------------|-------|
| appointment | patient | 105747 |

## Sample rows

| left_source_type | left_row_id | right_source_type | right_row_id | candidate_rule | score_raw | promotion_reason |
|------------------|-------------|-------------------|--------------|----------------|-----------|------------------|
| appointment | 437962 | patient | 22516 | A3_phone_exact_name_high_sim | 100.0 | A3_phone_exact_name_high_sim |
| appointment | 438401 | patient | 23601 | A3_phone_exact_name_high_sim | 100.0 | A3_phone_exact_name_high_sim |
| appointment | 438419 | patient | 23601 | A3_phone_exact_name_high_sim | 100.0 | A3_phone_exact_name_high_sim |
| appointment | 442682 | patient | 60743 | A3_phone_exact_name_high_sim | 100.0 | A3_phone_exact_name_high_sim |
| appointment | 443182 | patient | 11789 | A3_phone_exact_name_high_sim | 100.0 | A3_phone_exact_name_high_sim |
| appointment | 444347 | patient | 28042 | A3_phone_exact_name_high_sim | 100.0 | A3_phone_exact_name_high_sim |
| appointment | 444395 | patient | 28042 | A3_phone_exact_name_high_sim | 100.0 | A3_phone_exact_name_high_sim |
| appointment | 444647 | patient | 28042 | A3_phone_exact_name_high_sim | 100.0 | A3_phone_exact_name_high_sim |
| appointment | 446279 | patient | 60743 | A3_phone_exact_name_high_sim | 100.0 | A3_phone_exact_name_high_sim |
| appointment | 448267 | patient | 30271 | A3_phone_exact_name_high_sim | 100.0 | A3_phone_exact_name_high_sim |
| appointment | 451881 | patient | 32079 | A3_phone_exact_name_high_sim | 100.0 | A3_phone_exact_name_high_sim |
| appointment | 452365 | patient | 2764 | A3_phone_exact_name_high_sim | 100.0 | A3_phone_exact_name_high_sim |
| appointment | 452410 | patient | 2764 | A3_phone_exact_name_high_sim | 100.0 | A3_phone_exact_name_high_sim |
| appointment | 452698 | patient | 32525 | A3_phone_exact_name_high_sim | 100.0 | A3_phone_exact_name_high_sim |
| appointment | 452712 | patient | 32525 | A3_phone_exact_name_high_sim | 100.0 | A3_phone_exact_name_high_sim |

## Why B2_name_exact_only is excluded from safe promotion

B2 (name exact only) is **not** promoted to the safe table because:

- **No phone evidence:** A match on normalized name alone can link many payment/appointment rows to many patients (e.g. common names, family members sharing a surname).
- **High collision risk:** One name key can map to multiple patient_ids; promoting B2 would create ambiguous links.
- **Policy:** Safe promotion requires at least **phone exact** (A2, A3, B1) so that the same phone anchors the identity. B2 has no phone signal.

B2 remains in `identity_candidate_matches` for analysis and possible future fuzzy-review workflow, but is not written to `safe_identity_matches_phase2`.

---

*No updates were made to `patients` or `payments.patient_id`. This phase only populates the safe promotion table.*
