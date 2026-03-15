# Phase 3 Rule Diagnostics

Generated: 2026-03-15T13:49:58.723059

## Payment ↔ Appointment phone overlap (zero-candidate follow-up)

Diagnostic counts:
- **Distinct payment phones (mobile_primary_norm):** 0
- **Distinct appointment phones (phone_primary_norm):** 42077
- **Overlapping distinct phones:** 0

**Interpretation:** If overlapping_phones is 0 or very low, payment↔appointment B7 candidates will be zero. Likely causes: normalization mismatch, different source coverage (e.g. appointment files missing or different years), or real data sparsity. If both counts are high but overlap is low, investigate column mapping and normalization consistency.
