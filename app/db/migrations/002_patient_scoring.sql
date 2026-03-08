-- Migration: Add patient scoring system
-- Date: 2026-02-26
-- Description: Add priority scoring columns to appointments and patients tables

-- Add scoring columns to appointments table
ALTER TABLE appointments ADD COLUMN patient_priority_score REAL;
ALTER TABLE appointments ADD COLUMN insurance_score REAL;
ALTER TABLE appointments ADD COLUMN treatment_score REAL;
ALTER TABLE appointments ADD COLUMN tenure_score REAL;
ALTER TABLE appointments ADD COLUMN frequency_score REAL;

-- Add lifetime value score to patients table
ALTER TABLE patients ADD COLUMN lifetime_value_score REAL;

-- Create index on patient_priority_score for efficient high-value patient queries
CREATE INDEX idx_appointments_priority_score ON appointments(patient_priority_score DESC);
CREATE INDEX idx_patients_lifetime_value ON patients(lifetime_value_score DESC);
