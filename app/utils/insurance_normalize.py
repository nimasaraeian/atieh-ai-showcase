# -*- coding: utf-8 -*-
"""
Insurance name normalization for priority lookup.

Examples:
  "بیمه سامان 20%" → "سامان"
  "بیمه ملت 30%"  → "ملت"
  "CASH"          → "CASH"
"""
import re


def normalize_insurance_for_lookup(insurance_name: str) -> str:
    """
    Extract base insurance name for lookup in insurance_priority_rank.

    - Strips leading "بیمه " (optional space)
    - Removes trailing " XX%" or " X%" patterns
    - Returns trimmed string; empty input → empty string
    """
    if not insurance_name or not isinstance(insurance_name, str):
        return ""
    s = insurance_name.strip()
    if not s:
        return ""

    # Remove leading "بیمه " (بیمه = insurance in Persian)
    prefix = "بیمه"
    if s.startswith(prefix):
        s = s[len(prefix):].lstrip()

    # Remove trailing percentage like " 20%" or " ۱۰٪"
    s = re.sub(r'\s*[\d۰-۹٠-٩]+\s*[%٪]\s*$', '', s, flags=re.UNICODE)

    return s.strip()
