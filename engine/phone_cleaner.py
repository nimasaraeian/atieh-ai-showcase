# -*- coding: utf-8 -*-
"""
Phone Cleaner: Remove non-numeric noise from phone fields.

Removes: موبایل, تماس, tel, phone, کار, فالگیری, کشیدن, etc.
Replaces separators with space.
Handles partial numbers: 0914xxxxxxx, 914xxxxxxx (x -> 0).
"""

import re
from typing import List

# Noise words to remove (Persian + English)
NOISE_WORDS = [
    r"UNKNOWN[_\-]?",
    r"موبایل\s*:?",
    r"تماس\s*:?",
    r"تلفن\s*:?",
    r"شماره\s*:?",
    r"\btel\s*:?",
    r"\bphone\s*:?",
    r"کار\b",
    r"فالگیری",
    r"کشیدن",
    r"م\s+",  # م 09143482738
]
_NOISE_PAT = re.compile(
    "|".join(f"({w})" for w in NOISE_WORDS),
    re.IGNORECASE
)

# Separators and prefixes -> space (include + for intl)
_SEP = re.compile(r"[\s;,/\|\-_\(\)\[\]:+]+")

def clean_text(raw: str) -> str:
    """
    Remove noise, replace separators with space, normalize whitespace.

    Example:
      "موبایل:09141864468; تماس:04433664565" -> "09141864468 04433664565"
    """
    if raw is None or not isinstance(raw, str):
        return ""
    text = str(raw).strip()
    if not text:
        return ""

    # Remove noise words
    text = _NOISE_PAT.sub(" ", text)

    # Replace x/X with 0 when adjacent to digits (0914xxxxxxx -> 09140000000)
    def _replace_x(m):
        return m.group(1) + "0" * len(m.group(2))
    text = re.sub(r"(\d)([xX]+)", _replace_x, text)

    # Replace ... (truncation) after 4 digits with 0000000 (0914... -> 09140000000)
    text = re.sub(r"(\d{4})\.\.\.", r"\g<1>0000000", text)

    # Replace separators with space
    text = _SEP.sub(" ", text)

    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text
