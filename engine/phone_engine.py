# -*- coding: utf-8 -*-
"""
Phone Engine: Main pipeline combining clean -> extract -> classify -> normalize -> score.

Returns structured result for database storage.
"""

from typing import Any, Dict, List, Optional

from engine.phone_cleaner import clean_text
from engine.phone_extractor import extract_numbers
from engine.phone_classifier import classify_number
from engine.phone_normalizer import normalize_number
from engine.phone_scorer import TYPE_SCORE, best_candidate

MOBILE_TYPES = {"mobile", "mobile_missing_zero", "mobile_international"}


def process(raw: str) -> Dict[str, Any]:
    """
    Full pipeline: clean -> extract -> classify -> normalize -> score.

    Returns:
        {
            raw_phone: str,
            primary_mobile: str | None,
            secondary_mobile: str | None,
            landline: str | None,
            normalized_candidates: [(canonical, type), ...],
            phone_type: str,
            confidence_score: float,
            status: str,
        }
    """
    raw = raw if raw is not None else ""
    raw = str(raw).strip()

    cleaned = clean_text(raw)
    digits_list = extract_numbers(cleaned)
    normalized: List[tuple] = []
    for d in digits_list:
        canon, ptype = normalize_number(d)
        if canon and ptype != "invalid":
            normalized.append((canon, ptype))

    mobiles = [c for c, t in normalized if t in MOBILE_TYPES]
    landlines = [c for c, t in normalized if t == "landline" or t == "short_landline"]
    primary_mobile = mobiles[0] if mobiles else None
    secondary_mobile = mobiles[1] if len(mobiles) > 1 else None
    landline = landlines[0] if landlines else None

    conf, _, best_type = best_candidate(normalized)
    status = _status(raw, digits_list, normalized)
    phone_type = "multi_number" if len(normalized) > 1 else (best_type if normalized else "invalid")

    return {
        "raw_phone": raw if raw else None,
        "primary_mobile": primary_mobile,
        "secondary_mobile": secondary_mobile,
        "landline": landline,
        "all_candidates": digits_list,
        "normalized_candidates": normalized,
        "phone_type": phone_type,
        "confidence_score": conf,
        "status": status,
    }


def _status(raw: str, digits_list: List[str], normalized: List[tuple]) -> str:
    if not digits_list:
        return "invalid"
    if len(digits_list) > 1:
        return "multi_number"
    if not normalized:
        return "uncertain"
    raw_digits = "".join(c for c in raw if c.isdigit())
    if raw_digits == digits_list[0] and len(raw.strip()) == len(digits_list[0]):
        return "clean"
    return "parsed_with_noise"
