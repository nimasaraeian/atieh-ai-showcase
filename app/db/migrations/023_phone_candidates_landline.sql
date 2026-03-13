-- Migration 023: Add landline column to phone_candidates

ALTER TABLE phone_candidates ADD COLUMN landline TEXT;
