# -*- coding: utf-8 -*-
"""
Staff patient search API – returns ONLY staff-safe fields.
Uses existing token-based search, never exposes financial data.
"""
from typing import Optional

from fastapi import APIRouter, Query, Depends

from app.api.patient_search import search_patients as _search_patients_impl
from app.security.roles import serialize_staff_patient
from app.security.rbac import require_roles

router = APIRouter(
    prefix="/api/staff",
    tags=["Staff"],
    dependencies=[Depends(require_roles("receptionist", "clinic_manager"))],
)


@router.get("/patients/search")
def staff_patient_search(
    q: Optional[str] = Query(None, description="Search: name, mobile, or record_no"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    Staff-safe patient search. Returns only operational fields.
    Never exposes financial_tier or lifetime_payment.
    """
    raw = _search_patients_impl(q, limit=limit, offset=offset)
    rows = raw.get("data", [])

    # Map raw fields to format expected by serialize_staff_patient
    def _to_row(r):
        d = dict(r)
        d["last_payment_date"] = d.get("last_payment_date_raw")
        d["last_visit_date"] = d.get("last_visit_date_raw") or d.get("last_payment_date_raw")
        return d

    safe_data = [serialize_staff_patient(_to_row(r)) for r in rows]

    return {"count": len(safe_data), "data": safe_data}
