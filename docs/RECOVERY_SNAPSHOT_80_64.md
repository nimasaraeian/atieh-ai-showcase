# SNAPSHOT — Atieh AI Identity Resolution Engine

## Database
atieh_clinic_recovery81_test.db

## Final Recovery Status
- Recovered Patients: 113,318
- Total Patients: 140,457
- Coverage: 80.64%

## Major Recovery Sources
- patients_direct
- appointment_bridge_combined
- payments_recordno
- appointment_name_mobile_consensus

## Key Breakthrough
Appointment-based name + single-mobile consensus recovery added 38,555 additional patients.

## Previous Coverage
53.20%

## New Coverage
80.64%

## Remaining Unresolved
27,139 patients

## Key Tables Built
- payments_identity_clean_v3
- payments_recordno_patient_bridge_v3
- unrecovered_appointment_candidates
- unrecovered_appointment_candidates_scored_v2
- appointment_name_mobile_consensus_v1
- appointment_consensus_phone_recovery_v1
