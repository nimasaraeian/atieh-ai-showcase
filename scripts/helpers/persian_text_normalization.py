# -*- coding: utf-8 -*-
"""
Persian text normalization for identity resolution.
Used consistently across payments, appointments, and patients.
"""
from __future__ import annotations

import re
from typing import Optional


# Arabic to Persian character mapping
ARABIC_YEH = "\u064a"  # ي
ARABIC_KAF = "\u0643"  # ك
PERSIAN_YEH = "\u06cc"  # ی
PERSIAN_KAF = "\u06a9"  # ک

# Zero-width and directional
ZWNJ = "\u200c"
ZWJ = "\u200d"
ZWS = "\u200b"
LRM = "\u200e"
RLM = "\u200f"
BOM = "\ufeff"

# Persian/Arabic digits -> English
PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
ASCII_DIGITS = "0123456789"


def normalize_persian_text(raw: Optional[str]) -> str:
    """
    Apply consistent Persian text normalization for names.
    - Trim and collapse repeated spaces
    - Replace Arabic ي with Persian ی, ك with ک
    - Remove zero-width non-joiners when harmful
    - Normalize half-space inconsistencies
    - Remove decorative punctuation when non-essential
    - Preserve content; do not strip meaningful parentheses (e.g. tags)
    """
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s or s in ("nan", "None"):
        return ""
    # Zero-width and directional
    for ch in (ZWNJ, ZWJ, ZWS, LRM, RLM, BOM):
        s = s.replace(ch, " ")
    # Arabic to Persian
    s = s.replace(ARABIC_YEH, PERSIAN_YEH).replace("ى", PERSIAN_YEH)
    s = s.replace(ARABIC_KAF, PERSIAN_KAF)
    # Collapse spaces
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def remove_trailing_record_no_parens(text: str) -> str:
    """
    Remove enclosing parentheses if they only contain numeric record_no at the end.
    E.g. "نام بیمار (12345)" -> "نام بیمار"
    """
    if not text or not isinstance(text, str):
        return text or ""
    return re.sub(r"\s*\(\d{4,10}\)\s*$", "", text.strip()).strip()


def patient_name_norm(raw: Optional[str]) -> str:
    """
    Normalized patient name: Persian normalization + optional trailing (record_no) removal.
    Use for patient_name_norm field.
    """
    s = normalize_persian_text(raw)
    s = remove_trailing_record_no_parens(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def patient_name_key(raw: Optional[str]) -> str:
    """
    Stricter key for matching: compact, no spaces, no punctuation.
    Deterministic: remove spaces, remove punctuation, normalize, lowercase not applied (Persian).
    """
    s = patient_name_norm(raw)
    if not s:
        return ""
    # Remove punctuation and separators
    s = re.sub(r"[\s\-\.\,\;\:\'\"\(\)\[\]\{\}]+", "", s)
    return s


def digits_persian_arabic_to_english(s: Optional[str]) -> str:
    """Convert Persian and Arabic digits in string to ASCII 0-9."""
    if not s:
        return ""
    s = str(s)
    for i, p in enumerate(PERSIAN_DIGITS):
        s = s.replace(p, ASCII_DIGITS[i])
    for i, a in enumerate(ARABIC_DIGITS):
        s = s.replace(a, ASCII_DIGITS[i])
    return s


def national_id_norm(raw: Optional[str]) -> Optional[str]:
    """
    National ID: digits only, length 10. Return None if invalid.
    """
    if raw is None or (isinstance(raw, float) and str(raw) == "nan"):
        return None
    s = str(raw).strip()
    for ch in " \t.-/\\,_":
        s = s.replace(ch, "")
    s = digits_persian_arabic_to_english(s)
    s = "".join(c for c in s if c.isdigit())
    return s if len(s) == 10 else None


def record_no_norm(raw: Optional[str]) -> Optional[str]:
    """
    Record no: trim, digits only for matching. Empty -> None.
    (Some sources have alphanumeric; we use digits-only for deterministic matching.)
    """
    if raw is None or (isinstance(raw, float) and str(raw) == "nan"):
        return None
    s = str(raw).strip()
    if not s:
        return None
    s = digits_persian_arabic_to_english(s)
    s = "".join(c for c in s if c.isdigit())
    return s if s else None
