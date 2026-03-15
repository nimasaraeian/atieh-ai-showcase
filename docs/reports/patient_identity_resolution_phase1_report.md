# Patient Identity Resolution Phase 1 – Final Report

Generated: 2026-03-15T12:43:20.322616

## What was built

1. **appointments_unified_staging** – raw import of all yearly appointment Excel files
2. **identity_normalized_payments** – normalized identity from payments_unified_staging
3. **identity_normalized_appointments** – normalized identity from appointments_unified_staging
4. **patients_identity_normalized** – normalized identity from patients table
5. **identity_candidate_matches** – candidate pairings with rules and scores
6. **identity_clusters_proposed** – optional (not populated in phase 1)

## Metrics summary

- Total candidates: 0
- Tier A (high confidence): 0
- Tier B: 0
- Ambiguous (collision): 0
- payment↔patient candidates: 0
- appointment↔patient candidates: 0
- payment↔appointment candidates: 0

## K5) High-value answers

1. **Strongest identity bridge:** Phone exact + name exact (A2) and phone exact + high name similarity (A3). National ID is strong in payments but patients.national_id is empty, so A1 yields no payment↔patient link until patients get national_id.
2. **Payment↔appointment at scale:** Feasible via B7 (phone exact); count above.
3. **Appointment↔patient at scale:** Feasible via phone+name (A2/A3) and phone-only (B1) with review.
4. **Payment↔patient direct phone-based:** Feasible where phone and name align; Tier A/B counts above.
5. **High-confidence coverage:** Tier A + Tier B as percentage of total candidates and of total payment/appointment rows is in normalization and scoring reports.
6. **Phase 2:** (a) Final assignment layer for Tier A/B non-ambiguous only; (b) Appointment bridge promotion; (c) Record_no extraction improvement; (d) Fuzzy review workflow for Tier C/D.

## Limitations

- No final patient_id assignment to payments or patients.
- Persian name similarity threshold is strict to avoid over-match.
- payments 1403 has no separate record_no column; left null.
- patients.national_id is empty; national_id match to patients not used yet.

