# Patient Identity Resolution Phase 3 – Graph Expansion Report

**Scoring weights (documented):** record_no +80, phone +60, exact name +40, high name sim +25, repeated cluster phone/recordno +20 each, same year +10, date compatible +10. Penalties: one weak signal -50, phone match name conflict -35. Dominance margin: 15.

Generated: 2026-03-15T13:49:58.571118

## K1) Anchor metrics

- **Total anchor patients:** 27164
- **Anchor patients with primary_anchor (A2):** 27097
- **Average safe links per anchor patient:** 3.89

## K2) Anchor evidence metrics

- **Total distinct phones across anchors:** 45180
- **Total distinct record_nos:** 2
- **Total distinct names:** 27300
- **Anchors with multiple phones:** 21283
- **Anchors with multiple record_nos:** 0

## K3) Expansion candidate metrics

- **Total candidates generated:** 354738
- **By source_type:**
  - appointment: 42149
  - payment: 312589
- **By rule:**
  - P6_multi_signal_cluster_support: 286202
  - P2_repeated_anchored_phone_expansion: 22188
  - P4_phone_exact_name_inside_cluster: 17
- **By support_signal_count:**
  - 1: 46331
  - 2: 36814
  - 3: 252579
  - 4: 18606
  - 5: 408
- **Ambiguous candidates:** 4

## K4) Promotion metrics

- **Total promoted phase3 matches:** 1024
- **Promoted by rule:**
  - P2_repeated_anchored_phone_expansion: 994
  - P4_phone_exact_name_inside_cluster: 17
  - P6_multi_signal_cluster_support: 13
- **By confidence level:**
  - EXP_A: 1015
  - EXP_B: 9
- **Promoted payment count:** 0
- **Promoted appointment count:** 1024

## K5) Coverage metrics

- **Baseline unique recovered patients (before phase3):** 27164
- **Unique recovered patients after phase3:** 27164
- **Increase:** 0

*(Phase3 links more payment/appointment rows to existing anchor patients; distinct patient count may stay at baseline. To approach 80000 would require additional anchor sources.)*

- **Increase percentage:** 0.0%
- **Gap to 80000 target:** 52836

## K6) Safety metrics

- **Rejected ambiguous candidates:** 4
- **Top rules causing ambiguity:**
  - P2_repeated_anchored_phone_expansion: 4
- **REVIEW (not promoted):** 290997
- **REJECT:** 62680

## K7) Record_no diagnostics

- **Promotions from record_no-supported rules (P1, P3):** 0

## Sample promoted rows (phase3)

| source_type | source_row_id | target_patient_id | expansion_rule | support_signal_count | score_raw | confidence_level |
|-------------|---------------|-------------------|----------------|----------------------|-----------|------------------|
| appointment | 435206 | 67831 | P2_repeated_anchored_phone_expansion | 3 | 105.0 | EXP_A |
| appointment | 435328 | 366 | P2_repeated_anchored_phone_expansion | 3 | 105.0 | EXP_A |
| appointment | 435382 | 62606 | P2_repeated_anchored_phone_expansion | 3 | 105.0 | EXP_A |
| appointment | 435406 | 62606 | P2_repeated_anchored_phone_expansion | 3 | 105.0 | EXP_A |
| appointment | 435422 | 57704 | P2_repeated_anchored_phone_expansion | 3 | 120.0 | EXP_A |
| appointment | 435484 | 62606 | P2_repeated_anchored_phone_expansion | 3 | 105.0 | EXP_A |
| appointment | 435574 | 38762 | P2_repeated_anchored_phone_expansion | 3 | 105.0 | EXP_A |
| appointment | 435848 | 60743 | P2_repeated_anchored_phone_expansion | 3 | 120.0 | EXP_A |
| appointment | 436510 | 39637 | P2_repeated_anchored_phone_expansion | 3 | 105.0 | EXP_A |
| appointment | 436835 | 60612 | P2_repeated_anchored_phone_expansion | 3 | 105.0 | EXP_A |

---

## L) Reporting questions answered

1. **Unique patient anchors we started with:** 27164
2. **Unique patients covered after phase3:** 27164
3. **Additional patients recovered:** 0 (phase3 adds links to existing anchors; new distinct patients only if expansion linked previously unlinked records to anchors).
4. **Which expansion rule contributed the most:** See promoted by rule above.
5. **Did record_no materially improve coverage:** See K7; record_no-supported rules (P1, P3) contributed as above.
6. **Is phone still the main bridge:** Yes for phase2 anchors; phase3 expansion uses phone + record_no + name in combination.
7. **Candidates remaining ambiguous:** 4
8. **How close to 80000:** 27164 recovered; gap 52836. 80000 is an aspiration; actual coverage depends on data and safe rules.
9. **Recommended next phase:** Choose among: final assignment layer (write to staging only); iterative graph expansion phase 4; record_no strengthening; manual review queue for REVIEW; payment↔appointment bridge repair.
