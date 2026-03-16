# -*- coding: utf-8 -*-
"""
Reception API routes – patient search and profile by V2 identity layer.

  GET /api/reception/search-patient?q=
  GET /api/reception/patient/{patient_id}
  GET /api/reception/crm-code/{crm_code}
"""
from fastapi import APIRouter, HTTPException, Query, Depends

from app.security.rbac import require_roles

from app.api.reception.service import (
    search_reception_patient,
    get_reception_patient_by_id,
    get_reception_patient_by_crm_code,
)

router = APIRouter(
    prefix="/api/reception",
    tags=["Reception"],
    dependencies=[Depends(require_roles("receptionist", "clinic_manager"))],
)


@router.get("/search-patient")
def reception_search_patient(
    q: str | None = Query(None, description="Search by name, phone, CRM code, or patient ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Results per page (default 50)"),
):
    """
    Search reception patients (V2 master_patient_profile_v2).
    Returns top page_size results per page, sorted by relevance then tier/count/year.
    Response: count, data, page, page_size, total_pages, and per-row multi_crm_for_same_patient_flag.
    """
    result = search_reception_patient(q=q, page=page, page_size=page_size)
    return result


@router.get("/patient/{patient_id}")
def reception_get_patient(patient_id: int):
    """
    Get all linked profiles for a patient_id.
    One patient may have multiple CRM-code links; response includes all.
    """
    result = get_reception_patient_by_id(patient_id)
    return result


@router.get("/crm-code/{crm_code}")
def reception_get_by_crm_code(crm_code: str):
    """Get single profile by crm_patient_code."""
    result = get_reception_patient_by_crm_code(crm_code.strip())
    return result
