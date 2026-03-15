# -*- coding: utf-8 -*-
"""
Phone normalization for identity resolution.
Handles multi-value cells (; , / | etc.) and Iranian mobile format 09xxxxxxxxx.
"""
from __future__ import annotations

import json
import re
from typing import List, Tuple

try:
    from .persian_text_normalization import digits_persian_arabic_to_english
except ImportError:
    from scripts.helpers.persian_text_normalization import digits_persian_arabic_to_english

# Split on common separators for multi-phone cells
PHONE_SEP = re.compile(r"[/,\s;\|\-]+")


def _digits_only(s: str) -> str:
    """Extract digits only; convert Persian/Arabic digits to English."""
    s = digits_persian_arabic_to_english(s)
    return "".join(c for c in s if c.isdigit())


def _normalize_one_token(token: str) -> str | None:
    """
    One token -> digits only, then:
    - 0098... -> drop 0098
    - 98... (12+ digits) -> 0 + rest
    - 10 digits starting with 9 -> 0 + digits
    Valid: 11 digits, starts with 09.
    """
    digits = _digits_only(token)
    if not digits:
        return None
    if digits.startswith("0098") and len(digits) >= 12:
        digits = digits[4:]
    elif digits.startswith("98") and len(digits) >= 10:
        digits = digits[2:]
    if len(digits) == 10 and digits.startswith("9"):
        digits = "0" + digits
    if len(digits) > 11:
        digits = digits[-11:]
    if len(digits) == 11 and digits.startswith("09"):
        return digits
    return None


def normalize_phone_primary_and_all(raw: Optional[str]) -> Tuple[Optional[str], str]:
    """
    Parse raw phone field (possibly multi-value). Return (primary_norm, json_array_of_all_valid).
    Primary: first valid 09xxxxxxxxx in order after splitting.
    All: list of unique valid normalized numbers as JSON string.
    """
    if raw is None or (isinstance(raw, float) and str(raw) == "nan"):
        return None, "[]"
    s = str(raw).strip()
    if not s:
        return None, "[]"
    tokens = [t.strip() for t in PHONE_SEP.split(s) if t.strip()]
    seen = set()
    all_norm = []
    primary = None
    for t in tokens:
        n = _normalize_one_token(t)
        if n and n not in seen:
            seen.add(n)
            all_norm.append(n)
            if primary is None:
                primary = n
    return primary, json.dumps(all_norm, ensure_ascii=False) if all_norm else "[]"


def normalize_phone_primary(raw: Optional[str]) -> Optional[str]:
    """Convenience: return only primary normalized phone or None."""
    primary, _ = normalize_phone_primary_and_all(raw)
    return primary
