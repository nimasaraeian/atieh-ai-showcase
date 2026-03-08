"""
Payment type normalization utilities.

Used by both the importer and reprocess pipeline to ensure consistent,
canonical payment_type values are written to the database.

Canonical values
----------------
  'cash'        – نقدی / CASH / NAKİT
  'insurance'   – any insurance variant (INSURANCE_<n>, بیمه, sigorta, …)
  'card'        – card / POS / kart / kredi
  'transfer'    – transfer / havale / EFT / wire
  'installment' – installment / taksit / قسط
  'unknown'     – everything else
"""

import re
from typing import Optional


def normalize_payment_type(raw: Optional[str]) -> str:
    """
    Return the canonical payment-type string for *raw*.

    Args:
        raw: The raw payment-type text as received from the source (Excel
             column value, API field, etc.).  May be None or empty.

    Returns:
        One of: 'cash', 'insurance', 'card', 'transfer', 'installment',
        'unknown'.
    """
    if not raw:
        return "unknown"

    s = str(raw).strip()
    if not s or s.lower() in ("nan", "none", ""):
        return "unknown"

    su = s.upper()

    # ── insurance ────────────────────────────────────────────────────────────
    # INSURANCE_<n> legacy enum pattern (e.g. 'INSURANCE_5')
    if re.match(r"^INSURANCE_\d+$", su):
        return "insurance"
    # Free-text keyword variants (English / Persian / Turkish)
    if "INSURANCE" in su or "بیمه" in s or "SIGORTA" in su:
        return "insurance"

    # ── cash ─────────────────────────────────────────────────────────────────
    if su in ("CASH", "NAKIT", "NAKİT"):
        return "cash"
    if s in ("cash", "نقد", "نقدی"):
        return "cash"

    # ── card / POS ───────────────────────────────────────────────────────────
    if any(kw in su for kw in ("CARD", "POS", "KART", "KREDI")):
        return "card"

    # ── bank transfer ────────────────────────────────────────────────────────
    if any(kw in su for kw in ("TRANSFER", "HAVALE", "EFT", "WIRE")):
        return "transfer"

    # ── instalment ───────────────────────────────────────────────────────────
    if any(kw in su for kw in ("INSTALLMENT", "TAKSIT")) or "قسط" in s:
        return "installment"

    return "unknown"
