# -*- coding: utf-8 -*-
"""
Name cleanup and similarity for identity resolution.
Uses Persian normalization and optional fuzzy ratio.
"""
from __future__ import annotations

from typing import Optional, Tuple

try:
    from .persian_text_normalization import patient_name_norm, patient_name_key
except ImportError:
    from scripts.helpers.persian_text_normalization import patient_name_norm, patient_name_key


def name_exact_key_match(a_raw: Optional[str], b_raw: Optional[str]) -> bool:
    """True if patient_name_key(a) == patient_name_key(b) and both non-empty."""
    ka = patient_name_key(a_raw)
    kb = patient_name_key(b_raw)
    if not ka or not kb:
        return False
    return ka == kb


def name_similarity_score(a_raw: Optional[str], b_raw: Optional[str]) -> float:
    """
    Return similarity in 0–100 scale.
    Uses SequenceMatcher on normalized names; exact key match = 100.
    """
    na = patient_name_norm(a_raw)
    nb = patient_name_norm(b_raw)
    if not na and not nb:
        return 100.0
    if not na or not nb:
        return 0.0
    if patient_name_key(a_raw) == patient_name_key(b_raw):
        return 100.0
    try:
        from difflib import SequenceMatcher
        ratio = SequenceMatcher(None, na, nb).ratio()
        return round(ratio * 100.0, 2)
    except Exception:
        return 0.0


def name_exact_and_similarity(a_raw: Optional[str], b_raw: Optional[str]) -> Tuple[bool, float]:
    """Returns (name_exact_flag as bool, name_similarity_score 0–100)."""
    exact = name_exact_key_match(a_raw, b_raw)
    score = name_similarity_score(a_raw, b_raw) if not exact else 100.0
    return exact, score
