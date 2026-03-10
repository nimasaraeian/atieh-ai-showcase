# -*- coding: utf-8 -*-

import logging
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Body, HTTPException

from app.engine.db_schedule_recommender import recommend_slots_from_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ai/engine",
    tags=["AI Engine"],
)

DAY_MAP_FA_TO_EN = {
    "\u0634\u0646\u0628\u0647": "Saturday",
    "\u06cc\u06a9\u0634\u0646\u0628\u0647": "Sunday",
    "\u062f\u0648\u0634\u0646\u0628\u0647": "Monday",
    "\u0633\u0647 \u0634\u0646\u0628\u0647": "Tuesday",
    "\u0633\u0647\u200c\u0634\u0646\u0628\u0647": "Tuesday",
    "\u0686\u0647\u0627\u0631\u0634\u0646\u0628\u0647": "Wednesday",
    "\u067e\u0646\u062c\u0634\u0646\u0628\u0647": "Thursday",
    "\u062c\u0645\u0639\u0647": "Friday",
}


@router.post("/recommend-slot")
def recommend_slot(payload: dict = Body(...)):
    try:
        preferred_day = payload.get("preferred_day")

        if not preferred_day and payload.get("weekday"):
            weekday_value = str(payload.get("weekday")).strip()
            preferred_day = DAY_MAP_FA_TO_EN.get(weekday_value, weekday_value)

        db_payload = {
            "record_no": payload.get("record_no"),
            "service": payload.get("service"),
            "insurance": payload.get("insurance"),
            "preferred_day": preferred_day,
        }

        logger.info("recommend-slot raw payload=%r", payload)
        logger.info("recommend-slot mapped preferred_day=%r", preferred_day)

        result = recommend_slots_from_db(db_payload, top_n=200)

        logger.info(
            "recommend-slot completed | count=%s | preferred_day_input=%s | preferred_day_mapped=%s",
            result.get("count"),
            result.get("preferred_day_input"),
            result.get("preferred_day_mapped"),
        )

        return result

    except Exception as e:
        logger.exception("Scheduling engine failed")
        raise HTTPException(
            status_code=500,
            detail=f"Scheduling engine error: {e}",
        ) from e


def _resolve_catalog_path(candidates):
    for p in candidates:
        path = Path(p)
        if path.exists():
            return str(path)
    return None


@router.get("/catalog/services")
def get_services():
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

    col = next(
        (
            c for c in [
                "insurance_name",
                "insurer_name_norm",
                "payer_source_norm",
            ]
            if c in df.columns
        ),
        df.columns[0],
    )