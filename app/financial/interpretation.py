# -*- coding: utf-8 -*-
"""
Financial interpretation layer for patient profiling.

Computes interpretable financial metrics from payments_clean, including:
- Amount unit detection (rial)
- Net received in rial/toman
- Patient/insurer splits
- Positive/negative row counts (reversal patterns)
- Insurer normalization and dominant insurer
- Cash vs insurance row counts
- Confidence note for reversal/limitation awareness

Amounts in source Excel are stored in RIAL. Toman = Rial / 10.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional


# Cash-like labels (not insurers) – آزاد, نقد, etc.
CASH_LIKE_PATTERNS = (
    "آزاد",
    "نقد",
    "نقدی",
    "cash",
    "CASH",
)

# Canonical insurer mappings: (pattern, canonical)
# Handles variants like ایران10%, ایران 30 %, تامین اجتماعی(3), نیروهای مسلح(2)
INSURER_NORMALIZATION = [
    # تامین اجتماعی (various Unicode: ی/ي، ء)
    (r"تامین\s*اجتماعی", "تامین اجتماعی"),
    (r"تأمين\s*اجتماعي", "تامین اجتماعی"),
    (r"تامین\s*اجتماعي", "تامین اجتماعی"),
    (r"تامين\s*اجتماعي", "تامین اجتماعی"),
    # نیروهای مسلح
    (r"نیروهای\s*مسلح", "نیروهای مسلح"),
    (r"نيروهاي\s*مسلح", "نیروهای مسلح"),
    # ایران
    (r"ایران\s*\d*\s*%?", "ایران"),
    (r"ايران\s*\d*\s*%?", "ایران"),
    # آسیا
    (r"اسیا\s*\d*\s*%?", "آسیا"),
    (r"آسیا\s*\d*\s*%?", "آسیا"),
    (r"اسيا\s*\d*\s*%?", "آسیا"),
    # بیمه دی
    (r"بیمه\s*دی", "بیمه دی"),
    (r"بيمه\s*دي", "بیمه دی"),
    # البرز
    (r"البرز\s*\d*\s*درصد?", "البرز"),
    (r"البرز\s*\d*\s*%?", "البرز"),
    # سینا
    (r"سینا\s*\d*\s*%?", "سینا"),
    (r"سينا\s*\d*\s*%?", "سینا"),
    # دانا
    (r"دانا\s*\d*\s*%?", "دانا"),
    # بانک ملی، ملت، تجارت، سپه، صدا و سیما، کشاورزی، ملی بازنشسته، جانبازان، دانا
    (r"بانک\s*ملی\s*شاغل", "بانک ملی شاغل"),
    (r"بانک\s*ملت", "بانک ملت"),
    (r"صدا\s*و\s*سیما\s*شاغل", "صدا و سیما شاغل"),
    (r"کشاورزی", "کشاورزی"),
    (r"ملی\s*بازنشسته", "ملی بازنشسته"),
    (r"سپه", "سپه"),
    (r"تجارت", "تجارت"),
    (r"جانبازان\s*نیروهای\s*مسلح", "جانبازان نیروهای مسلح"),
    (r"جانبازان\s*نيروهاي\s*مسلح", "جانبازان نیروهای مسلح"),
    (r"دانا\s*\d*\s*%?", "دانا"),
]


def _is_cash_like(insurer_raw: Optional[str]) -> bool:
    if not insurer_raw or not isinstance(insurer_raw, str):
        return False
    s = insurer_raw.strip()
    if not s:
        return False
    for pat in CASH_LIKE_PATTERNS:
        if pat in s:
            return True
    return False


def normalize_insurer(insurer_raw: Optional[str]) -> Optional[str]:
    """
    Map raw insurer label to canonical name.
    Returns None for cash-like labels (they are not insurers).
    """
    if not insurer_raw or not isinstance(insurer_raw, str):
        return None
    s = insurer_raw.strip()
    if not s:
        return None
    if _is_cash_like(s):
        return None
    for pattern, canonical in INSURER_NORMALIZATION:
        if re.search(pattern, s, re.IGNORECASE):
            return canonical
    # If no pattern matched, try stripping trailing (digits) and % / درصد
    base = re.sub(r"\s*\(?\d+\)?\s*$", "", s)
    base = re.sub(r"\s*\d*\s*%?\s*درصد?\s*$", "", base)
    base = base.strip()
    return base if base else s


@dataclass
class PatientFinancialInterpretation:
    """Interpreted financial profile for a patient (by record_no)."""

    record_no: str
    amount_unit_detected: str = "rial"
    net_received_rial: float = 0.0
    net_received_toman: float = 0.0
    amount_patient_rial: float = 0.0
    amount_patient_toman: float = 0.0
    amount_insurer_rial: float = 0.0
    amount_insurer_toman: float = 0.0
    payment_row_count: int = 0
    positive_row_count: int = 0
    negative_row_count: int = 0
    last_payment_date_raw: Optional[str] = None
    dominant_payment_mode: Optional[str] = None
    insurer_count: int = 0
    normalized_insurer_list: list[str] = field(default_factory=list)
    dominant_insurer: Optional[str] = None
    financial_confidence_note: Optional[str] = None
    cash_row_count: int = 0
    insurance_row_count: int = 0
    # For backward compat with existing UI
    cash_txn_count: int = 0
    insurance_txn_count: int = 0
    lifetime_net_received: float = 0.0  # in toman for display
    financial_value_score: Optional[float] = None
    financial_tier: Optional[str] = None
    lifetime_txn_count: int = 0


def _compute_dominant_mode(cash_count: int, insurance_count: int) -> Optional[str]:
    if cash_count > 0 and insurance_count == 0:
        return "cash"
    if insurance_count > 0 and cash_count == 0:
        return "insurance"
    if cash_count > 0 and insurance_count > 0:
        return "mixed"
    return None


def compute_financial_interpretation(
    rows: list[dict[str, Any]],
    record_no: str,
) -> PatientFinancialInterpretation:
    """
    Compute interpreted financial profile from payments_clean rows for one record_no.

    rows: list of dicts with keys: net_received, amount_patient, amount_insurer,
          appointment_date_raw, payer_source_norm, insurer_raw
    """
    out = PatientFinancialInterpretation(record_no=record_no)

    if not rows:
        out.financial_confidence_note = "بدون رکورد پرداخت"
        return out

    net_sum = 0.0
    patient_sum = 0.0
    insurer_sum = 0.0
    pos_count = 0
    neg_count = 0
    cash_count = 0
    insurance_count = 0
    insurer_freq: dict[str, int] = {}
    last_date: Optional[str] = None

    for r in rows:
        net = float(r.get("net_received") or 0)
        pat = float(r.get("amount_patient") or 0)
        ins = float(r.get("amount_insurer") or 0)
        net_sum += net
        patient_sum += pat
        insurer_sum += ins
        if net > 0:
            pos_count += 1
        elif net < 0:
            neg_count += 1

        ps = (r.get("payer_source_norm") or "").strip().lower()
        ir = r.get("insurer_raw") or ""
        inorm = (r.get("insurer_name_norm") or "").strip()

        if ps == "cash" or _is_cash_like(ir) or _is_cash_like(inorm):
            cash_count += 1
        else:
            insurance_count += 1
            canon = normalize_insurer(inorm) if inorm else normalize_insurer(ir)
            if canon:
                insurer_freq[canon] = insurer_freq.get(canon, 0) + 1

        date_raw = r.get("appointment_date_raw") or r.get("loaded_at") or ""
        if date_raw and (last_date is None or str(date_raw) > str(last_date)):
            last_date = str(date_raw).strip() or None

    out.net_received_rial = net_sum
    out.net_received_toman = round(net_sum / 10.0, 0)
    out.amount_patient_rial = patient_sum
    out.amount_patient_toman = round(patient_sum / 10.0, 0)
    out.amount_insurer_rial = insurer_sum
    out.amount_insurer_toman = round(insurer_sum / 10.0, 0)
    out.payment_row_count = len(rows)
    out.positive_row_count = pos_count
    out.negative_row_count = neg_count
    out.last_payment_date_raw = last_date
    out.cash_row_count = cash_count
    out.insurance_row_count = insurance_count
    out.cash_txn_count = cash_count
    out.insurance_txn_count = insurance_count
    out.lifetime_net_received = round(net_sum / 10.0, 0)
    out.lifetime_txn_count = len(rows)
    out.dominant_payment_mode = _compute_dominant_mode(cash_count, insurance_count)

    out.normalized_insurer_list = sorted(insurer_freq.keys())
    out.insurer_count = len(out.normalized_insurer_list)
    if insurer_freq:
        out.dominant_insurer = max(insurer_freq, key=insurer_freq.get)

    # Confidence note
    notes = []
    if neg_count > 0:
        notes.append("وجود ردیف‌های منفی (اصلاح حسابداری)؛ مبالغ خالص صرفاً بر اساس جمع ردیف‌ها.")
    if pos_count > 0 and neg_count > 0:
        notes.append("الگوی جفت شدن مثبت/منفی احتمالاً اصلاح یا کنسلی است.")
    if not notes:
        notes.append("جمع ردیف‌های دریافتی خالص.")
    out.financial_confidence_note = " ".join(notes)

    return out


def to_profile_dict(interp: PatientFinancialInterpretation) -> dict[str, Any]:
    """
    Convert to dict suitable for financial_profile in API response.
    Keeps existing UI fields and adds new ones.
    """
    d = {
        "record_no": interp.record_no,
        "amount_unit_detected": interp.amount_unit_detected,
        "net_received_rial": interp.net_received_rial,
        "net_received_toman": interp.net_received_toman,
        "amount_patient_rial": interp.amount_patient_rial,
        "amount_patient_toman": interp.amount_patient_toman,
        "amount_insurer_rial": interp.amount_insurer_rial,
        "amount_insurer_toman": interp.amount_insurer_toman,
        "payment_row_count": interp.payment_row_count,
        "positive_row_count": interp.positive_row_count,
        "negative_row_count": interp.negative_row_count,
        "last_payment_date_raw": interp.last_payment_date_raw,
        "dominant_payment_mode": interp.dominant_payment_mode,
        "insurer_count": interp.insurer_count,
        "normalized_insurer_list": interp.normalized_insurer_list,
        "dominant_insurer": interp.dominant_insurer,
        "financial_confidence_note": interp.financial_confidence_note,
        "cash_row_count": interp.cash_row_count,
        "insurance_row_count": interp.insurance_row_count,
        # Backward compat
        "cash_txn_count": interp.cash_txn_count,
        "insurance_txn_count": interp.insurance_txn_count,
        "lifetime_net_received": interp.lifetime_net_received,
        "lifetime_txn_count": interp.lifetime_txn_count,
    }
    if interp.financial_value_score is not None:
        d["financial_value_score"] = interp.financial_value_score
    if interp.financial_tier is not None:
        d["financial_tier"] = interp.financial_tier
    return d
