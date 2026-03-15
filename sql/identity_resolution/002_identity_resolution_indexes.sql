-- =============================================================================
-- Identity Resolution Engine – Indexes for performance
-- =============================================================================

-- appointments_unified_staging
CREATE INDEX IF NOT EXISTS idx_aus_source_file ON appointments_unified_staging(source_file);
CREATE INDEX IF NOT EXISTS idx_aus_shamsi_year ON appointments_unified_staging(shamsi_year);
CREATE INDEX IF NOT EXISTS idx_aus_phone_raw ON appointments_unified_staging(phone_raw) WHERE phone_raw IS NOT NULL AND TRIM(phone_raw) <> '';

-- identity_normalized_payments
CREATE INDEX IF NOT EXISTS idx_inp_payments_staging_id ON identity_normalized_payments(payments_staging_id);
CREATE INDEX IF NOT EXISTS idx_inp_mobile_primary_norm ON identity_normalized_payments(mobile_primary_norm) WHERE mobile_primary_norm IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_inp_national_id_norm ON identity_normalized_payments(national_id_norm) WHERE national_id_norm IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_inp_record_no_norm ON identity_normalized_payments(record_no_norm) WHERE record_no_norm IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_inp_patient_name_key ON identity_normalized_payments(patient_name_key) WHERE patient_name_key IS NOT NULL AND TRIM(patient_name_key) <> '';
CREATE INDEX IF NOT EXISTS idx_inp_shamsi_year ON identity_normalized_payments(shamsi_year);

-- identity_normalized_appointments
CREATE INDEX IF NOT EXISTS idx_ina_appointment_staging_id ON identity_normalized_appointments(appointment_staging_id);
CREATE INDEX IF NOT EXISTS idx_ina_phone_primary_norm ON identity_normalized_appointments(phone_primary_norm) WHERE phone_primary_norm IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ina_national_id_norm ON identity_normalized_appointments(national_id_norm) WHERE national_id_norm IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ina_record_no_norm ON identity_normalized_appointments(record_no_norm) WHERE record_no_norm IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ina_patient_name_key ON identity_normalized_appointments(patient_name_key) WHERE patient_name_key IS NOT NULL AND TRIM(patient_name_key) <> '';
CREATE INDEX IF NOT EXISTS idx_ina_shamsi_year ON identity_normalized_appointments(shamsi_year);

-- patients_identity_normalized
CREATE INDEX IF NOT EXISTS idx_pin_patient_id ON patients_identity_normalized(patient_id);
CREATE INDEX IF NOT EXISTS idx_pin_phone_primary_norm ON patients_identity_normalized(phone_primary_norm) WHERE phone_primary_norm IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_pin_national_id_norm ON patients_identity_normalized(national_id_norm) WHERE national_id_norm IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_pin_record_no_norm ON patients_identity_normalized(record_no_norm) WHERE record_no_norm IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_pin_patient_name_key ON patients_identity_normalized(patient_name_key) WHERE patient_name_key IS NOT NULL AND TRIM(patient_name_key) <> '';

-- identity_candidate_matches
CREATE INDEX IF NOT EXISTS idx_icm_left ON identity_candidate_matches(left_source_type, left_row_id);
CREATE INDEX IF NOT EXISTS idx_icm_right ON identity_candidate_matches(right_source_type, right_row_id);
CREATE INDEX IF NOT EXISTS idx_icm_confidence_tier ON identity_candidate_matches(confidence_tier);
CREATE INDEX IF NOT EXISTS idx_icm_match_status ON identity_candidate_matches(match_status);
CREATE INDEX IF NOT EXISTS idx_icm_candidate_rule ON identity_candidate_matches(candidate_rule);
CREATE INDEX IF NOT EXISTS idx_icm_score_raw ON identity_candidate_matches(score_raw) WHERE score_raw IS NOT NULL;

-- identity_clusters_proposed
CREATE INDEX IF NOT EXISTS idx_icp_source ON identity_clusters_proposed(source_type, source_row_id);
CREATE INDEX IF NOT EXISTS idx_icp_confidence_tier ON identity_clusters_proposed(confidence_tier);
