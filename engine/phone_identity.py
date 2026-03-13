# -*- coding: utf-8 -*-
"""
Phone Identity: Backward-compatible API delegating to phone_engine.
"""

from typing import List, Optional, Tuple

from engine.phone_engine import process

Status = str


def score(raw: str) -> float:
    """Return confidence score [0, 1]."""
    result = process(raw)
    return result["confidence_score"]


def resolve(raw: str) -> Tuple[
    float, Status, List[str], List[tuple],
    Optional[str], Optional[str], Optional[str]
]:
    """
    Full resolve. Returns:
        (confidence, status, raw_candidates, normalized_candidates,
         primary_mobile, secondary_mobile, phone_type)
    """
    result = process(raw)
    norm_list = result["normalized_candidates"]
    return (
        result["confidence_score"],
        result["status"],
        result["all_candidates"],
        norm_list,
        result["primary_mobile"],
        result["secondary_mobile"],
        result["phone_type"],
    )
