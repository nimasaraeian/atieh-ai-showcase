-- =============================================================================
-- Identity Resolution Phase 2: Safe Promotion Layer
-- Promotes Tier A non-ambiguous candidates only. Does NOT update patients or payments.
-- =============================================================================

CREATE TABLE IF NOT EXISTS safe_identity_matches_phase2 (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    left_source_type     TEXT NOT NULL,
    left_row_id          INTEGER NOT NULL,
    right_source_type    TEXT NOT NULL,
    right_row_id         INTEGER NOT NULL,
    candidate_rule        TEXT NOT NULL,
    score_raw            REAL,
    confidence_tier      TEXT NOT NULL DEFAULT 'A',
    match_status        TEXT NOT NULL,
    promotion_reason     TEXT NOT NULL,   -- 'primary_anchor' | 'A3_phone_exact_name_high_sim' | 'B1_phone_exact_only'
    created_at           TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_safe_phase2_left ON safe_identity_matches_phase2(left_source_type, left_row_id);
CREATE INDEX IF NOT EXISTS idx_safe_phase2_right ON safe_identity_matches_phase2(right_source_type, right_row_id);
CREATE INDEX IF NOT EXISTS idx_safe_phase2_rule ON safe_identity_matches_phase2(candidate_rule);
CREATE INDEX IF NOT EXISTS idx_safe_phase2_promotion_reason ON safe_identity_matches_phase2(promotion_reason);
