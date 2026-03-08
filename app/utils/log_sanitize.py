"""
Log-safe helpers: avoid double-quote artifacts and malformed normalized values in logs.
"""
from typing import Optional

from app.utils.text_normalize import normalize_doctor_name


def safe_repr(s: Optional[str]) -> str:
    """
    Return a representation suitable for logs without double-quoting artifacts.
    Use repr() so quotes and special chars are properly escaped.
    """
    return repr(s) if s is not None else "None"


def safe_norm_doctor(s: Optional[str]) -> str:
    """
    Normalize doctor name and return a clean string for logging.
    - Uses canonical normalize_doctor_name() pipeline
    - Strips leading/trailing whitespace
    - Strips surrounding single/double quotes (defensive)
    - Collapses repeated internal quotes ('' -> ') until stable
    """
    if s is None:
        return ""
    out = normalize_doctor_name(s)
    out = out.strip()
    # Strip surrounding quotes
    quote_chars = ("'", '"', '"', '"', "'", "'")
    while out and out[0] in quote_chars:
        out = out[1:].strip()
    while out and out[-1] in quote_chars:
        out = out[:-1].strip()
    # Collapse '' -> ' until stable
    prev = None
    while prev != out:
        prev = out
        out = out.replace("''", "'")
    return out.strip()
