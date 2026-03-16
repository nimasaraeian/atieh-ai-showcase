# -*- coding: utf-8 -*-
"""
Receptionist finalize booking API.
Persists AI-recommended slot selections to ai_finalized_bookings table.
"""

import os
import sqlite3
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Body, Depends
from pydantic import BaseModel

logger = logging.getLogger(__name__)

from app.security.rbac import require_roles

router = APIRouter(
    prefix="/api/receptionist",
    tags=["Receptionist"],
    dependencies=[Depends(require_roles("receptionist", "clinic_manager"))],
)


def _get_db_path() -> str:
    # Prefer ATIEH_DB_PATH for consistency with the rest of the app, but keep
    # DATABASE_URL compatibility for existing deployments.
    env_db = os.getenv("ATIEH_DB_PATH")
    if env_db:
        return env_db
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
            receptionist_user TEXT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            source TEXT NOT NULL DEFAULT 'AI',
            status TEXT NOT NULL DEFAULT 'confirmed'
        )
    """)
    conn.commit()


def _ensure_columns(conn: sqlite3.Connection) -> None:
    """
    Ensure optional columns exist (backward compatible upgrades).
    Safe to run on every request.
    """
    try:
        cur = conn.cursor()
        cols = cur.execute("PRAGMA table_info(ai_finalized_bookings)").fetchall()
        existing = {str(r[1]) for r in cols}  # (cid, name, type, notnull, dflt_value, pk)
        if "receptionist_user" not in existing:
            cur.execute("ALTER TABLE ai_finalized_bookings ADD COLUMN receptionist_user TEXT NULL")
            conn.commit()
        if "is_reverted" not in existing:
            cur.execute("ALTER TABLE ai_finalized_bookings ADD COLUMN is_reverted INTEGER NOT NULL DEFAULT 0")
            conn.commit()
        if "reverted_at" not in existing:
            cur.execute("ALTER TABLE ai_finalized_bookings ADD COLUMN reverted_at TEXT NULL")
            conn.commit()
        if "reverted_by" not in existing:
            cur.execute("ALTER TABLE ai_finalized_bookings ADD COLUMN reverted_by TEXT NULL")
            conn.commit()
        if "revert_reason" not in existing:
            cur.execute("ALTER TABLE ai_finalized_bookings ADD COLUMN revert_reason TEXT NULL")
            conn.commit()
    except sqlite3.OperationalError:
        return


class FinalizeBookingRequest(BaseModel):
    record_no: str
    patient_name: str
    doctor_name: Optional[str] = None  # Optional when clinic-level slot (no doctor selected)
    service: str
    date: str
    time: str
    receptionist_user: Optional[str] = None


class RevertBookingRequest(BaseModel):
    reverted_by: Optional[str] = None
    revert_reason: Optional[str] = None


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
    receptionist_user = (payload.receptionist_user or "").strip() or None

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
        _ensure_columns(conn)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO ai_finalized_bookings
                (record_no, patient_name, doctor_name, service, date, time, receptionist_user, source, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'AI', 'confirmed')
            """,
            (record_no, patient_name, doctor_name, service, date_val, time_val, receptionist_user),
        )
        conn.commit()
        row_id = cur.lastrowid
        row = cur.execute(
            """
            SELECT
              id, record_no, patient_name, doctor_name, service, date, time,
              receptionist_user, created_at, source, status,
              COALESCE(is_reverted, 0) AS is_reverted,
              reverted_at, reverted_by, revert_reason
            FROM ai_finalized_bookings
            WHERE id = ?
            """,
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
        _ensure_table(conn)
        _ensure_columns(conn)
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT
                  id, record_no, patient_name, doctor_name, service, date, time,
                  receptionist_user, created_at, source, status,
                  COALESCE(is_reverted, 0) AS is_reverted,
                  reverted_at, reverted_by, revert_reason
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


@router.post("/finalized-bookings/{booking_id}/revert")
def revert_finalized_booking(booking_id: int, payload: RevertBookingRequest = Body(default=RevertBookingRequest())):
    """
    Revert a finalized booking without deleting it (auditable).

    Rules:
    - Only existing bookings can be reverted.
    - A booking can be reverted only once.
    - Reverting marks status='reverted' and sets is_reverted=1 + audit fields.
    """
    db_path = _get_db_path()
    if not os.path.exists(db_path):
        raise HTTPException(status_code=503, detail="Database not available")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        _ensure_table(conn)
        _ensure_columns(conn)
        cur = conn.cursor()

        row = cur.execute(
            """
            SELECT
              id, record_no, patient_name, doctor_name, service, date, time,
              receptionist_user, created_at, source, status,
              COALESCE(is_reverted, 0) AS is_reverted,
              reverted_at, reverted_by, revert_reason
            FROM ai_finalized_bookings
            WHERE id = ?
            LIMIT 1
            """,
            (int(booking_id),),
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="finalized booking not found")

        current = dict(row)
        if int(current.get("is_reverted") or 0) == 1 or str(current.get("status") or "").lower() == "reverted":
            raise HTTPException(status_code=409, detail="booking already reverted")

        reverted_by = (payload.reverted_by or "").strip() or None
        revert_reason = (payload.revert_reason or "").strip() or None

        cur.execute(
            """
            UPDATE ai_finalized_bookings
            SET
              status = 'reverted',
              is_reverted = 1,
              reverted_at = datetime('now'),
              reverted_by = ?,
              revert_reason = ?
            WHERE id = ?
            """,
            (reverted_by, revert_reason, int(booking_id)),
        )
        conn.commit()

        updated = cur.execute(
            """
            SELECT
              id, record_no, patient_name, doctor_name, service, date, time,
              receptionist_user, created_at, source, status,
              COALESCE(is_reverted, 0) AS is_reverted,
              reverted_at, reverted_by, revert_reason
            FROM ai_finalized_bookings
            WHERE id = ?
            LIMIT 1
            """,
            (int(booking_id),),
        ).fetchone()

        return {"ok": True, "before": current, "after": dict(updated) if updated else None}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.exception("revert_finalized_booking failed")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
