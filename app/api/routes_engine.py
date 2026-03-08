# -*- coding: utf-8 -*-
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
import os

from app.engine.run_engine import run as run_engine

router = APIRouter(prefix="/ai/engine", tags=["ai-engine"])


class EngineRequest(BaseModel):
    service: str = Field(..., description="مثلا: کشیدن دندان")
    insurance: Optional[str] = Field(None, description="مثلا: ایران")
    backlog: Optional[str] = Field(None, description="مثلا: درمان ریشه")
    doctor: Optional[int] = Field(None, description="مثلا: 1009")
    weekday: Optional[str] = Field(None, description="مثلا: پنجشنبه")


@router.post("/recommend-slot")
def recommend_slot(req: EngineRequest) -> Dict[str, Any]:
    payload = {"service_name": req.service}
    if req.insurance is not None:
        payload["insurance_name"] = req.insurance
    if req.backlog is not None:
        payload["backlog_title"] = req.backlog
    if req.doctor is not None:
        payload["preferred_doctor_id"] = req.doctor
    if req.weekday is not None:
        payload["preferred_weekday"] = req.weekday
    result = run_engine(payload)

    rec_path = os.path.join("data", "outputs", "slot_recommendations.csv")
    draft_path = os.path.join("data", "outputs", "schedule_draft.csv")

    return {
        "ok": True,
        "input": req.model_dump(),
        "result": result,
        "outputs": {
            "slot_recommendations_csv": rec_path if os.path.exists(rec_path) else None,
            "schedule_draft_csv": draft_path if os.path.exists(draft_path) else None,
        },
    }