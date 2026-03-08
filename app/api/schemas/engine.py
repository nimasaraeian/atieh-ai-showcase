from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List


class EngineRecommendRequest(BaseModel):
    service: str = Field(..., description="نام سرویس درمانی مثل کشیدن دندان")
    insurance: Optional[str] = None
    backlog: Optional[str] = None
    doctor: Optional[int] = None
    weekday: Optional[str] = None


class EngineRecommendResponse(BaseModel):
    run_id: str
    input: Dict[str, Any]
    draft: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    counts: Dict[str, int]