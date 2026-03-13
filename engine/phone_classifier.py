# -*- coding: utf-8 -*-
"""
Phone Classifier: Classify numbers by pattern.

Types:
  09xxxxxxxxx -> mobile
  9xxxxxxxxx -> mobile_missing_zero
  00989xxxxxxxxx -> mobile_international
  +989xxxxxxxxx -> mobile_international
  0xxxxxxxxxx -> landline
  xxxxxxxx (7-10 digits) -> short_landline
  <6 digits -> invalid
"""

from typing import List, Tuple

PhoneType = str  # 'mobile' | 'mobile_missing_zero' | 'mobile_international' | 'landline' | 'short_landline' | 'invalid'


def classify_number(digits: str) -> PhoneType:
    """
    Classify a digit-only string.
    """
    if not digits or not digits.isdigit():
        return "invalid"
    n = len(digits)
    if n < 6:
        return "invalid"
    if n == 11 and digits.startswith("09"):
        return "mobile"
    if n == 10 and digits.startswith("9"):
        return "mobile_missing_zero"
    if n == 14 and digits.startswith("00989"):
        return "mobile_international"
    if n == 12 and digits.startswith("989"):
        return "mobile_international"
    if n == 11 and digits.startswith("0") and digits[1] != "9":
        return "landline"
    if n == 12 and digits.startswith("98") and digits[2] != "9":
        return "landline"
    if n == 14 and digits.startswith("0098") and digits[4] != "9":
        return "landline"
    if 7 <= n <= 10:
        return "short_landline"
    return "invalid"


def classify_numbers(digits_list: List[str]) -> List[Tuple[str, PhoneType]]:
    """Classify each digit string. Returns [(digits, type), ...]"""
    return [(d, classify_number(d)) for d in digits_list]
    # compatibility wrapper for older imports

class Status:
    MOBILE = "mobile"
    LANDLINE = "landline"
    INVALID = "invalid"


def classify(digits: str):
    return classify_number(digits)
