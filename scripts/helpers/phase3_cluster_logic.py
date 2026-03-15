# -*- coding: utf-8 -*-
"""
Phase 3: Cluster-local evidence flags.
Repeated phone/record_no = observed more than once for the same anchor patient.
"""
from __future__ import annotations

from typing import Set, Dict, Any


def repeated_cluster_phone(observation_count: int, min_repeat: int = 2) -> bool:
    """True if this phone appears multiple times in the anchor cluster."""
    return observation_count >= min_repeat


def repeated_cluster_recordno(observation_count: int, min_repeat: int = 2) -> bool:
    """True if this record_no appears multiple times in the anchor cluster."""
    return observation_count >= min_repeat


def high_name_similarity_threshold(score: float) -> bool:
    """Name similarity >= 85 (0-100 scale) counts as high for expansion."""
    return score >= 85.0 if score is not None else False


def date_compatible(d1: str | None, d2: str | None) -> bool:
    """Simple compatibility: same year substring or both non-null. Can be refined."""
    if not d1 or not d2:
        return False
    # Extract 4-digit year if present
    for s in (d1, d2):
        if len(s) >= 4 and s[:4].isdigit():
            break
    else:
        return True
    y1 = d1[:4] if len(d1) >= 4 and d1[:4].isdigit() else None
    y2 = d2[:4] if len(d2) >= 4 and d2[:4].isdigit() else None
    if y1 and y2:
        return y1 == y2
    return True
