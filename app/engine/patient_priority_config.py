# -*- coding: utf-8 -*-
"""
Patient priority scheduling: configurable weights, tiers, and scheduling windows.

Weights (0–100 normalized patient_priority_score):
- insurance_score: 25%
- visit_score: 20%
- relationship_score: 15%
- financial_score: 30%
- recency_score: 10%

Tiers: P1 (Elite) … P7 (Low).
Scheduling windows: how many days from today the patient can be offered slots.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Weights for composite patient_priority_score (must sum to 1.0)
WEIGHTS = {
    "insurance_score": 0.25,
    "visit_score": 0.20,
    "relationship_score": 0.15,
    "financial_score": 0.30,
    "recency_score": 0.10,
}

# Tier labels (7 levels)
TIER_NAMES = {
    "P1": "Elite",
    "P2": "Premium",
    "P3": "High",
    "P4": "Strong",
    "P5": "Medium",
    "P6": "Basic",
    "P7": "Low",
}

# Score bands for tier assignment (patient_priority_score 0–100)
# Tier is the first band where score >= min_score
TIER_BANDS = [
    {"tier": "P1", "min_score": 85, "label": "Elite"},
    {"tier": "P2", "min_score": 72, "label": "Premium"},
    {"tier": "P3", "min_score": 60, "label": "High"},
    {"tier": "P4", "min_score": 48, "label": "Strong"},
    {"tier": "P5", "min_score": 35, "label": "Medium"},
    {"tier": "P6", "min_score": 20, "label": "Basic"},
    {"tier": "P7", "min_score": 0, "label": "Low"},
]

# Scheduling window: (min_days, max_days) from today for slot date.
# IMPORTANT (clinic ops):
# - Must remain near-term and actionable for receptionist workflow.
# - Do NOT use long-range windows (e.g. 365 days) in normal flow.
# - If a long-range policy is ever needed, it must be implemented explicitly
#   as a separate, intentional business rule (not via default tier mapping).
SCHEDULING_WINDOWS = {
    # Very high priority: allow very near-term, but still give some flexibility.
    "P1": (0, 5),
    # High priority: near-term with small buffer.
    "P2": (0, 7),
    # Good: practical short window.
    "P3": (1, 10),
    # Medium-high: operational planning window.
    "P4": (2, 12),
    # Normal: typical clinic window.
    "P5": (3, 14),
    # Lower tiers: still actionable; allow slightly later, but keep it within 3 weeks.
    "P6": (3, 21),
    "P7": (3, 21),
}

# Preferred window is the range we *want* to schedule inside (soft preference),
# while allowed window is the hard constraint enforced by the recommender.
# Preferred must be a subset of allowed.
#
# NOTE: These are operational defaults. Any exception that allows pushing
# a slot outside preferred must be explicit and surfaced in UI reasons.
PREFERRED_WINDOWS = {
    "P1": (0, 3),
    "P2": (2, 6),
    "P3": (4, 10),
    "P4": (4, 10),
    "P5": (5, 12),
    # Low-importance patients: prefer later within allowed (avoid "today" taking top rank).
    "P6": (10, 21),
    "P7": (17, 21),
}


def get_scheduling_window_days(tier: str) -> tuple[int, int]:
    """Return (min_days, max_days) for the given tier. Default P5 if unknown."""
    t = (tier or "").strip().upper()
    if t in SCHEDULING_WINDOWS:
        return SCHEDULING_WINDOWS[t]
    return SCHEDULING_WINDOWS["P5"]


def get_scheduling_window_model(tier: str) -> dict[str, tuple[int, int]]:
    """
    Return {'allowed': (min,max), 'preferred': (min,max)} for a tier.
    Ensures preferred is clamped inside allowed.
    """
    t = (tier or "").strip().upper()
    allowed = SCHEDULING_WINDOWS.get(t, SCHEDULING_WINDOWS["P5"])
    preferred = PREFERRED_WINDOWS.get(t, PREFERRED_WINDOWS.get("P5", allowed))
    a0, a1 = allowed
    p0, p1 = preferred
    p0 = max(a0, int(p0))
    p1 = min(a1, int(p1))
    if p1 < p0:
        p0, p1 = a0, a1
    return {"allowed": (int(a0), int(a1)), "preferred": (int(p0), int(p1))}


def get_tier_for_score(score: float) -> str:
    """Return tier (e.g. P1–P7) for a 0–100 patient_priority_score."""
    try:
        s = float(score)
    except (TypeError, ValueError):
        return "P7"
    for band in TIER_BANDS:
        if s >= band["min_score"]:
            return band["tier"]
    return "P7"


def get_tier_label(tier: str) -> str:
    """Return display label for tier."""
    return TIER_NAMES.get((tier or "").strip().upper(), "Low")
