# Patient Identity Resolution Phase 4 – Runbook (Graph Propagation)

## Goal

Multi-hop identity graph propagation: expand recovered patients using **phase4_patient_graph_nodes**, **phase4_phone_patient_links**, **phase4_name_patient_links**, with propagation rules A–H and scoring. No global name-only or phone-only promotion; cluster-supported and dominance applied.

## Environment

```powershell
$env:ATIEH_DB_PATH = "atieh_clinic_recovery81_test.db"
```

## Prerequisites

- Phase 2 and 3: `safe_identity_matches_phase2`, `identity_expansion_promoted_phase3`, `identity_anchor_patients_phase3`, `identity_anchor_phone_phase3`, `identity_anchor_name_phase3`, `identity_anchor_profile_phase3`.
- Optional: Phase 3B (`unrecovered_patients_phase3b`).

## Run order

1. **Graph and links**
   ```powershell
   python scripts/build_phase4_graph_and_links.py
   ```
   Populates: phase4_patient_graph_nodes, phase4_patient_graph_edges, phase4_phone_patient_links, phase4_name_patient_links.

2. **Cluster candidates**
   ```powershell
   python scripts/build_phase4_cluster_candidates.py
   ```
   Populates: phase4_cluster_candidates (unrecovered → cluster with flags and rule).

3. **Score and promote**
   ```powershell
   python scripts/promote_phase4_cluster_candidates.py
   ```
   Populates: phase4_cluster_promoted, phase4_ambiguity_review; updates phase4_cluster_candidates (score_raw, confidence_level, match_status).

4. **Stats and report**
   ```powershell
   python scripts/identity_phase4_graph_stats.py
   ```
   Populates: phase4_patient_recovered; writes **patient_identity_resolution_phase4_graph_propagation_report.md**.

## Generated report

- **docs/reports/patient_identity_resolution_phase4_graph_propagation_report.md**  
  Newly recovered, total recovered, coverage %, promotion by rule, ambiguity count, growth from primary vs all vs multi-hop, realistic upper bound toward 100k.

## Safety

- No updates to `patients` or `payments.patient_id`.
- No global name-only or phone-only promotion; dominance margin 15.
