# -*- coding: utf-8 -*-
"""
Phone Parser: Backward-compatible extraction delegating to phone_engine.
"""

from typing import List

from engine.phone_cleaner import clean_text
from engine.phone_extractor import extract_numbers


def parse_phone_candidates(raw: str) -> List[str]:
    """Extract digit sequences (backward compat)."""
    cleaned = clean_text(raw or "")
    return extract_numbers(cleaned)
