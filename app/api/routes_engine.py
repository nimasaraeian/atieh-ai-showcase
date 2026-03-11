# -*- coding: utf-8 -*-
from fastapi import APIRouter, Body
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict

from app.engine.db_schedule_recommender import recommend_slots_from_db

router = APIRouter(prefix="/ai/engine", tags=["ai-engine"])


class EngineRequest(BaseModel):
    record_no: Optional[str] = Field(None, description="شماره پرونده بیمار")
    service: str = Field(..., description="مثلاً: کشیدن دندان")
    insurance: Optional[str] = Field(None, description="مثلاً: ایران")
    backlog: Optional[str] = Field(None, description="مثلاً: درمان ریشه")
    doctor: Optional[int] = Field(None, description="مثلاً: 1009")
    weekday: Optional[str] = Field(None, description="مثلاً: دوشنبه")


@router.post("/recommend-slot")
def recommend_slot(req: EngineRequest) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "service": req.service,
        "preferred_day": req.weekday,
        "insurance": req.insurance,
        "record_no": req.record_no,
        "backlog": req.backlog,
        "doctor": req.doctor,
    }
    return recommend_slots_from_db(payload, top_n=50)


@router.post("/recommend-slot-db")
def recommend_slot_db(payload: dict = Body(...)):
    return recommend_slots_from_db(payload, top_n=50)
