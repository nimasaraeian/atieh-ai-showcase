# -*- coding: utf-8 -*-
"""
Receptionist finalize booking API.
Persists AI-recommended slot selections to ai_finalized_bookings table.
"""

import os
import sqlite3
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/receptionist",
    tags=["Receptionist"],
)


def _get_db_path() -> str:
    db_url = os.getenv("DATABASE_URL", "sqlite:///atieh_clinic.db")
    if db_url.startswith("sqlite:///"):
        return db_url[len("sqlite:///"):]
    return db_url


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_finalized_bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_no TEXT NOT NULL,
            patient_name TEXT NOT NULL,
            doctor_name TEXT NOT NULL,
            service TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            source TEXT NOT NULL DEFAULT 'AI',
            status TEXT NOT NULL DEFAULT 'confirmed'
        )
    """)
    conn.commit()


class FinalizeBookingRequest(BaseModel):
    record_no: str
    patient_name: str
    doctor_name: Optional[str] = None  # Optional when clinic-level slot (no doctor selected)
    service: str
    date: str
    time: str


@router.post("/finalize-booking")
def finalize_booking(payload: FinalizeBookingRequest = Body(...)):
    """
    Persist an AI-recommended booking to ai_finalized_bookings.
    Returns the created booking record.
    When no doctor was selected, doctor_name may be empty; stored as "—" for traceability.
    """
    record_no = (payload.record_no or "").strip()
    patient_name = (payload.patient_name or "").strip()
    doctor_name = (payload.doctor_name or "").strip() or "—"
    service = (payload.service or "").strip()
    date_val = (payload.date or "").strip()
    time_val = (payload.time or "").strip()

    if not record_no or not patient_name or not service or not date_val or not time_val:
        raise HTTPException(
            status_code=400,
            detail="record_no, patient_name, service, date, and time are required",
        )

    db_path = _get_db_path()
    if not os.path.exists(db_path):
        raise HTTPException(status_code=503, detail="Database not available")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        _ensure_table(conn)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO ai_finalized_bookings
                (record_no, patient_name, doctor_name, service, date, time, source, status)
            VALUES (?, ?, ?, ?, ?, ?, 'AI', 'confirmed')
            """,
            (record_no, patient_name, doctor_name, service, date_val, time_val),
        )
        conn.commit()
        row_id = cur.lastrowid
        row = cur.execute(
            "SELECT id, record_no, patient_name, doctor_name, service, date, time, created_at, source, status FROM ai_finalized_bookings WHERE id = ?",
            (row_id,),
        ).fetchone()
        return dict(row)
    except Exception as e:
        conn.rollback()
        logger.exception("finalize_booking failed")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.get("/finalized-bookings")
def get_finalized_bookings(limit: int = 100):
    """Return recent AI-finalized bookings for display in receptionist UI."""
    db_path = _get_db_path()
    if not os.path.exists(db_path):
        return {"ok": True, "data": []}

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT id, record_no, patient_name, doctor_name, service, date, time, created_at, source, status
                FROM ai_finalized_bookings
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (min(limit, 200),),
            )
            rows = cur.fetchall()
            return {"ok": True, "data": [dict(r) for r in rows]}
        except sqlite3.OperationalError:
            return {"ok": True, "data": []}
    finally:
        conn.close()
