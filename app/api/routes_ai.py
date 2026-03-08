"""
AI routes (record_no-first).
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any

from database import get_db
from app.ai.financial_boost import apply_financial_boost

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/priority/record-no/{record_no}")
async def priority_by_record_no(
    record_no: str,
    urgent: int = 0,
    base_score: float = 50.0,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    RecordNo-first priority score (financial injection).
    urgent=1 activates urgency guardrail (lower max boost).
    """
    try:
        conn = db.connection().connection
        result = apply_financial_boost(
            conn=conn,
            base_score=float(base_score),
            record_no=record_no,
            is_urgent=bool(int(urgent)),
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top/priority-records")
async def top_priority_records(
    limit: int = Query(50, ge=1, le=500),
    urgent: int = Query(0, ge=0, le=1),
    base_score: float = Query(50.0, ge=0.0, le=100.0),
    prefetch: int = Query(200, ge=1, le=5000),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Fetch the top `prefetch` record_nos by financial_value_score, apply
    financial boost to each, then return the top `limit` rows sorted by
    ai_priority_score descending.
    """
    try:
        rows = db.execute(
            text("""
                SELECT record_no
                FROM v_financial_for_engine_recordno
                ORDER BY financial_value_score DESC
                LIMIT :prefetch
            """),
            {"prefetch": prefetch},
        ).fetchall()

        conn = db.connection().connection
        scored = [
            apply_financial_boost(
                conn=conn,
                base_score=float(base_score),
                record_no=str(r[0]),
                is_urgent=bool(int(urgent)),
            )
            for r in rows
        ]

        scored.sort(key=lambda x: x["ai_priority_score"], reverse=True)
        return scored[:limit]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top/financial-records")
async def top_financial_records(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Returns top record_no rows by financial_value_score (independent of patient mapping).
    """
    rows = db.execute(
        text("""
            SELECT
              record_no,
              financial_value_score,
              lifetime_net_received,
              lifetime_txn_count,
              recent_net_received,
              recent_txn_count,
              last_payment_date_raw
            FROM v_financial_for_engine_recordno
            ORDER BY financial_value_score DESC
            LIMIT :limit
        """),
        {"limit": limit},
    ).fetchall()

    return [
        {
            "record_no": r[0],
            "financial_value_score": float(r[1]) if r[1] is not None else 0.0,
            "lifetime_net_received": float(r[2]) if r[2] is not None else 0.0,
            "lifetime_txn_count": int(r[3]) if r[3] is not None else 0,
            "recent_net_received": float(r[4]) if r[4] is not None else 0.0,
            "recent_txn_count": int(r[5]) if r[5] is not None else 0,
            "last_payment_date_raw": r[6],
        }
        for r in rows
    ]
