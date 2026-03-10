# -*- coding: utf-8 -*-
"""
Role policy and safe field lists for Atieh AI.

Staff: operational access only (no financial data).
Manager: full access including financial insights.
"""
from typing import Any, Dict, List, Optional

# Role constants
ROLE_STAFF = "staff"
ROLE_MANAGER = "manager"

# Fields safe for staff (no financial exposure)
STAFF_PATIENT_FIELDS = [
    "patient_name",
    "mobile_display",
    "mobile",  # alias for frontend compatibility
    "record_no",
    "last_visit_date",
    "last_payment_date",
    "last_payment_date_raw",  # alias for frontend
    "in_top300",
    "in_followup_queue",
]

# Fields for manager (includes financial)
MANAGER_PATIENT_FIELDS = [
    "patient_name",
    "mobile_display",
    "record_no",
    "last_visit_date",
    "last_payment_date",
    "lifetime_payment",
    "financial_tier",
    "financial_value_score",
]


def _format_mobile(raw: Any) -> str:
    """Hide UNKNOWN_* placeholders from staff/manager display."""
    s = str(raw or "").strip()
    if not s:
        return "-"
    if s.upper().startswith("UNKNOWN_"):
        return "موبایل نامشخص"
    return s


def serialize_staff_patient(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter a database row to staff-safe fields only.
    Never exposes financial_tier, lifetime_payment, or financial_value_score.
    """
    allowed = set(STAFF_PATIENT_FIELDS)
    out: Dict[str, Any] = {}

    # Map DB column names to output names
    patient_name = row.get("patient_name") or row.get("patient_name_canonical") or "-"
    mobile_raw = row.get("mobile") or row.get("mobile_canonical") or ""
    record_no = row.get("record_no") or "-"
    last_visit = row.get("last_visit_date") or row.get("last_visit_date_raw") or "-"
    last_payment = row.get("last_payment_date") or row.get("last_payment_date_raw") or "-"

    out["patient_name"] = patient_name
    out["mobile_display"] = _format_mobile(mobile_raw)
    out["mobile"] = out["mobile_display"]  # frontend compatibility
    out["record_no"] = record_no
    out["last_visit_date"] = last_visit
    out["last_payment_date"] = last_payment
    out["last_payment_date_raw"] = last_payment  # frontend compatibility
    out["in_top300"] = bool(row.get("in_top300"))
    out["in_followup_queue"] = bool(row.get("in_followup_queue"))

    return {k: v for k, v in out.items() if k in allowed}


def serialize_manager_patient(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter a database row to manager-safe fields.
    Includes financial tier and lifetime payment.
    """
    allowed = set(MANAGER_PATIENT_FIELDS)
    base = serialize_staff_patient(row)

    lifetime = row.get("lifetime_payment") or row.get("lifetime_net_received")
    base["lifetime_payment"] = lifetime
    base["financial_tier"] = row.get("financial_tier") or "-"
    base["financial_value_score"] = row.get("financial_value_score")

    return {k: v for k, v in base.items() if k in allowed}
