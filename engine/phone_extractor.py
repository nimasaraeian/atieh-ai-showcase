# -*- coding: utf-8 -*-
"""
Phone Extractor: Extract numeric sequences using regex.

Pattern: \\d{5,15} - do not assume format.
"""

import re
from typing import List

# Extract sequences of 5-15 digits
_DIGIT_SEQ = re.compile(r"\d{5,15}")


def extract_numbers(text: str) -> List[str]:
    """
    Extract all numeric sequences of 5-15 digits.

    Args:
        text: Cleaned text (from phone_cleaner).

    Returns:
        List of digit strings.
    """
    if not text or not isinstance(text, str):
        return []
    matches = _DIGIT_SEQ.findall(text)
    seen: set = set()
    result: List[str] = []
    for m in matches:
        if m not in seen:
            seen.add(m)
            result.append(m)
    return result
