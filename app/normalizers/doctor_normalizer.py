# -*- coding: utf-8 -*-
"""
Doctor name normalization for Atieh AI analytics.

Cleans raw_text_doctor values for consistent analytics and filters.
"""

import re
from typing import Optional, Tuple

# Specialty suffixes to strip (Persian)
SPECIALTY_PATTERNS = [
    r"\s*عمومی\s*$",
    r"\s*متخصص\s+پریو\s*$",
    r"\s*متخصص\s+ترمیمی\s*$",
    r"\s*متخصص\s+ریشه\s*$",
    r"\s*متخصص\s+فک\s+و\s+صورت\s*$",
    r"\s*متخصص\s+ارتودنسی\s*$",
    r"\s*متخصص\s+اطفال\s*$",
    r"\s*متخصص\s+جراحی\s*$",
    r"\s*پریو\s*$",
    r"\s*ترمیمی\s*$",
    r"\s*ریشه\s*$",
    r"\s*فک\s+و\s+صورت\s*$",
    r"\s*ارتودنسی\s*$",
    r"\s*اطفال\s*$",
    r"\s*جراحی\s*$",
]

PREFIX_PATTERNS = [
    r"^دکتر\s+",
    r"^دكتر\s+",
    r"^د\.\s*",
]


def _normalize_persian(s: str) -> str:
    """Normalize Persian/Arabic characters and whitespace."""
    if not s:
        return ""
    s = s.strip()
    s = s.replace("ي", "ی").replace("ك", "ک").replace("ة", "ه")
    s = s.replace("ى", "ی").replace("ؤ", "و").replace("إ", "ا").replace("أ", "ا")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def normalize_doctor(raw: Optional[str]) -> Tuple[str, Optional[str]]:
    """
    Normalize raw doctor text to clean_doctor_name and optional specialty.

    Returns:
        (clean_doctor_name, doctor_specialty)
    """
    if not raw or not str(raw).strip():
        return "", None

    s = _normalize_persian(str(raw))
    if not s:
        return "", None

    specialty = None
    for pat in SPECIALTY_PATTERNS:
        m = re.search(pat, s, re.IGNORECASE)
        if m:
            specialty = m.group(0).strip()
            s = re.sub(pat, "", s, flags=re.IGNORECASE)
            break

    for pat in PREFIX_PATTERNS:
        s = re.sub(pat, "", s, flags=re.IGNORECASE)

    s = _normalize_persian(s)
    if not s:
        s = _normalize_persian(str(raw))[:50]  # fallback to truncated raw
    return s, specialty


def get_clean_doctor_name(raw: Optional[str]) -> str:
    """Convenience: return only clean_doctor_name."""
    name, _ = normalize_doctor(raw)
    return name
