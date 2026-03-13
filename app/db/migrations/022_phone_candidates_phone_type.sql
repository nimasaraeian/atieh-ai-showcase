-- Migration 022: Add phone_type to phone_candidates
-- Stores: mobile | landline | short_landline | invalid

ALTER TABLE phone_candidates ADD COLUMN phone_type TEXT;
