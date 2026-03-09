# -*- coding: utf-8 -*-
"""
POST /ai/engine/recommend-slot – Atieh AI Smart Scheduling Engine (real engine, per-request outputs).

# Test with PowerShell (run from repo root, server on 8001):
#   $body = '{"service":"کشیدن دندان","insurance":"ایران","backlog":"درمان ریشه","doctor":1009,"weekday":"پنجشنبه"}'
#   Invoke-RestMethod -Uri "http://127.0.0.1:8001/ai/engine/recommend-slot" -Method Post -ContentType "application/json; charset=utf-8" -Body $body
"""
import logging

from fastapi import APIRouter, HTTPException

from app.api.schemas.engine import EngineRecommendRequest, EngineRecommendResponse
from app.api.services.engine_runner import run_engine_and_load_results

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai/engine", tags=["AI Engine"])


@router.post("/recommend-slot", response_model=EngineRecommendResponse)
def recommend_slot(req: EngineRecommendRequest):
    try:
        result = run_engine_and_load_results(
            service=req.service,
            insurance=req.insurance,
            backlog=req.backlog,
            doctor=req.doctor,
            weekday=req.weekday,
        )
        logger.info("run_id=%s completed", result["run_id"])
        return result
    except FileNotFoundError as e:
        logger.error("run failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        logger.exception("Engine execution failed")
        raise HTTPException(status_code=500, detail=f"Engine execution failed: {e}") from e


# ── Catalog endpoints for frontend dropdowns ─────────────────────────────────────


def _resolve_catalog_path(candidates):
    """Return first existing path from candidates, or None."""
    from pathlib import Path
    for p in candidates:
        path = Path(p)
        if path.exists():
            return str(path)
    return None


@router.get("/catalog/services")
def get_services():
    """
    Return list of unique service names from reference catalog.
    Returns [] if no catalog file found.
    """
    import pandas as pd

    path = _resolve_catalog_path([
        "data/reference/services_catalog.csv",
        "data/outputs/services_catalog.csv",
        "data/inputs/reference/services_catalog.csv",
    ])
    if not path:
        logger.warning("services catalog not found; returning empty list")
        return []
    df = pd.read_csv(path, encoding="utf-8-sig")
    col = "service_name" if "service_name" in df.columns else df.columns[0]
    return df[col].dropna().astype(str).unique().tolist()


@router.get("/catalog/insurances")
def get_insurances():
    """
    Return list of unique insurance names from reference catalog.
    Returns [] if no catalog file found.
    """
    import pandas as pd

    path = _resolve_catalog_path([
        "data/reference/insurance_payment_priority.csv",
        "data/outputs/insurance_priority.csv",
        "data/inputs/payments/insurance_payment_priority.csv",
        "data/reference/insurance_priority.csv",
    ])
    if not path:
        logger.warning("insurance catalog not found; returning empty list")
        return []
    df = pd.read_csv(path, encoding="utf-8-sig")
    col = next((c for c in ["insurance_name", "insurer_name_norm", "payer_source_norm"] if c in df.columns), df.columns[0])
    return df[col].dropna().astype(str).unique().tolist()