# -*- coding: utf-8 -*-
"""
Shared Persian name normalization for Atieh AI identity resolution.

Ensures consistent name matching between patients, stg_payments,
and appointment_recordno_bridge.
"""
from __future__ import annotations

import re
from typing import Optional


def normalize_persian_name(text: Optional[str]) -> str:
    """
    Normalize Persian/Arabic name for identity matching.
    - Trim, collapse spaces
    - Arabic -> Persian char mapping
    - Remove ZWNJ, punctuation
    - Sort tokens for order-invariant matching (e.g. "جعفر مرتاض" == "مرتاض جعفر")
    """
    if not text:
        return ""
    t = str(text).strip()

    # Arabic to Persian (same as app.importers.common.normalize)
    t = t.replace("\u064a", "\u06cc")  # ي -> ی
    t = t.replace("\u0649", "\u06cc")  # ى -> ی
    t = t.replace("\u0643", "\u06a9")  # ك -> ک
    t = t.replace("\u0629", "\u0647")  # ة -> ه
    t = t.replace("\u0624", "\u0648")  # ؤ -> و
    t = t.replace("\u0625", "\u0627")  # إ -> ا
    t = t.replace("\u0623", "\u0627")  # أ -> ا
    t = t.replace("\u0671", "\u0627")  # ٱ -> ا
    t = t.replace("\u0621", "")        # ء remove

    # Remove zero-width non-joiner and similar
    t = t.replace("\u200c", "")   # ZWNJ
    t = t.replace("\u200f", "")   # RTL mark
    t = t.replace("\ufeff", "")   # BOM
    t = t.replace("\u0640", "")   # Tatweel

    # Remove punctuation: , ؛ ؛ : - _ / \ . ( )
    for ch in ",،;؛:;_/\\.":
        t = t.replace(ch, " ")
    t = re.sub(r"[\(\\)\（\）]", " ", t)

    # Collapse spaces
    t = re.sub(r"\s+", " ", t).strip()

    # Sort tokens for order-invariant key
    tokens = [x for x in t.split() if x]
    tokens.sort()
    return " ".join(tokens)
