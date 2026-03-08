"""Canonical Persian doctor-name normalization utilities.

This module provides a single entry point for normalizing doctor names
used across recommender, scheduler, and logging.

It deliberately wraps the existing implementation in ``app.utils.doctor_name``
to avoid behavior changes, while adding a few extra guarantees:

- Returns ``""`` for None/empty inputs
- Ensures ZWNJ/ZWJ are treated as spacing and then collapses whitespace
"""

from typing import Optional
import re

from app.utils.doctor_name import normalize_doctor_name as _base_normalize


def normalize_doctor_name(s: Optional[str]) -> str:
    """Normalize a Persian doctor name for matching and logging.

    Behavior (inherited from ``app.utils.doctor_name`` + small post-processing):

    - Unify Arabic/Persian chars (e.g. ي→ی, ك→ک, ة→ه, أ/إ/آ→ا)
    - Remove common doctor prefixes (\"دکتر\", \"دكتر\", \"Dr.\", etc., case-insensitive)
    - Remove quotes/apostrophes anywhere in the string
    - Replace zero-width joiners with a space, collapse multiple spaces, strip
    - Return \"\" for None/empty inputs
    """
    if s is None:
        return ""

    # Delegate core logic to the existing, battle-tested normalizer.
    out = _base_normalize(s)
    if not out:
        return ""

    # Treat ZWNJ/ZWJ as spacing boundaries, then normalize whitespace.
    out = out.replace("\u200c", " ").replace("\u200d", " ")
    out = re.sub(r"\s+", " ", out).strip()
    return out


def normalize_doctor_key(name: Optional[str]) -> str:
    """
    Compute a stable key for doctor-name matching.

    Rules:
    - Run through canonical normalize_doctor_name first (prefixes, Arabic/Persian, quotes)
    - Remove any parentheses content, e.g. "(اطفال)"
    - Collapse spaces
    - If multi-word, return last token as the key (surname-ish)
    """
    if not name:
        return ""
    s = normalize_doctor_name(name)
    if not s:
        return ""

    # remove parentheses content
    s = re.sub(r"\(.*?\)", "", s)
    # normalize spaces
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        return ""

    parts = s.split(" ")
    return parts[-1]


