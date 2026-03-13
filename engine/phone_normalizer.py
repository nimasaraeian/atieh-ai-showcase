# -*- coding: utf-8 -*-
"""
Phone Normalizer: Normalize Iranian phones to canonical 98xxxxxxxxxx.

Examples:
  09141864468 -> 989141864468
  9141499299 -> 989141499299
  00989141864468 -> 989141864468
  04433664565 -> 984433664565
  32256242 (short_landline) -> 9832256242
"""

from typing import List, Optional, Tuple

from engine.phone_classifier import PhoneType, classify_number


def normalize_number(digits: str) -> Tuple[Optional[str], PhoneType]:
    """
    Normalize digit string to 98xxxxxxxxxx.

    Returns:
        (canonical, phone_type) or (None, "invalid")
    """
    if not digits or not digits.isdigit():
        return None, "invalid"
    ptype = classify_number(digits)
    n = len(digits)

    if ptype == "mobile":
        if n == 11:
            return "98" + digits[1:], ptype
        if digits.startswith("989") and n == 12:
            return digits, ptype
        if digits.startswith("00989") and n == 14:
            return digits[2:], ptype
    if ptype == "mobile_missing_zero":
        return "98" + digits, ptype
    if ptype == "mobile_international":
        if digits.startswith("989") and n == 12:
            return digits, ptype
        if digits.startswith("00989") and n == 14:
            return digits[2:], ptype
    if ptype == "landline":
        if n == 11:
            return "98" + digits[1:], ptype
        if digits.startswith("98") and n == 12:
            return digits, ptype
        if digits.startswith("0098") and n == 14:
            return digits[2:], ptype
    if ptype == "short_landline":
        return "98" + digits, ptype
    return None, "invalid"


def normalize_numbers(digits_list: List[str]) -> List[Tuple[str, PhoneType]]:
    """Normalize each, skip invalid. Returns [(canonical, type), ...]"""
    result: List[Tuple[str, str]] = []
    seen: set = set()
    for d in digits_list:
        canon, ptype = normalize_number(d)
        if canon and canon not in seen:
            seen.add(canon)
            result.append((canon, ptype))
    return result
