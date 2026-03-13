# -*- coding: utf-8 -*-
"""
Phone Scorer: Score candidates by type.

mobile = 0.95
mobile_missing_zero = 0.90
mobile_international = 0.90
landline = 0.75
short_landline = 0.50
invalid = 0

Prefer mobile over landline when multiple exist.
"""

from typing import List, Tuple

TYPE_SCORE = {
    "mobile": 0.95,
    "mobile_missing_zero": 0.90,
    "mobile_international": 0.90,
    "landline": 0.75,
    "short_landline": 0.50,
    "invalid": 0.0,
}


def score_number(canonical: str, phone_type: str) -> float:
    """Return score for a single normalized candidate."""
    return TYPE_SCORE.get(phone_type, 0.0)


def best_candidate(normalized: List[Tuple[str, str]]) -> Tuple[float, str, str]:
    """
    Prefer mobile over landline. Return (score, canonical, phone_type).
    """
    if not normalized:
        return 0.0, "", "invalid"
    best = max(normalized, key=lambda x: TYPE_SCORE.get(x[1], 0.0))
    return TYPE_SCORE.get(best[1], 0.0), best[0], best[1]
