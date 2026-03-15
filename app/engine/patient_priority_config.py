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
# P1: 0–3, P2: 0–5, P3: 0–7, P4: 0–10, P5: 0–14, P6: 7–21, P7: 14+
SCHEDULING_WINDOWS = {
    "P1": (0, 3),
    "P2": (0, 5),
    "P3": (0, 7),
    "P4": (0, 10),
    "P5": (0, 14),
    "P6": (7, 21),
    "P7": (14, 365),
}


def get_scheduling_window_days(tier: str) -> tuple[int, int]:
    """Return (min_days, max_days) for the given tier. Default P5 if unknown."""
    t = (tier or "").strip().upper()
    if t in SCHEDULING_WINDOWS:
        return SCHEDULING_WINDOWS[t]
    return SCHEDULING_WINDOWS["P5"]


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
