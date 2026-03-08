# -*- coding: utf-8 -*-
"""
Financial operational API – exposes operational views from the data pipeline.

Endpoints:
  GET /financial/followup/contactable  – v_financial_followup_queue_contactable
  GET /financial/followup/daily        – v_financial_followup_daily_balanced
  GET /financial/scheduling/top300     – v_financial_scheduling_queue_top300

Database: atieh_clinic_working.db (or FINANCIAL_DB_PATH env). Falls back to atieh_clinic.db.
"""

import os
import logging
import sqlite3
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)

# Prefer atieh_clinic_working.db (operational pipeline output); fallback to atieh_clinic.db
DB_PATH = os.environ.get("FINANCIAL_DB_PATH") or (
    "atieh_clinic_working.db"
    if os.path.exists("atieh_clinic_working.db")
    else "atieh_clinic.db"
)

router = APIRouter(prefix="/financial", tags=["Financial Operational"])


def get_financial_db():
    """Return SQLite connection for financial operational views."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _query_view(view_name: str, limit: int, offset: int, order_cols: str, extra_where: str = ""):
    """Generic helper to query a view with limit/offset."""
    conn = get_financial_db()
    try:
        cur = conn.cursor()
        where = f" WHERE {extra_where}" if extra_where else ""
        sql = f"SELECT * FROM {view_name}{where} ORDER BY {order_cols} LIMIT ? OFFSET ?"
        cur.execute(sql, (limit, offset))
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── Followup contactable ─────────────────────────────────────────────────────
@router.get("/followup/contactable")
def get_followup_contactable(
    limit: int = Query(500, ge=1, le=2000, description="Max rows"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    search: Optional[str] = Query(None, description="Search name or mobile"),
):
    """
    Read from v_financial_followup_queue_contactable.

    Returns: patient_name_canonical, mobile_canonical, financial_tier, action_type,
    action_priority_score, last_payment_date_raw, lifetime_net_received, followup_recommendation.
    """
    try:
        conn = get_financial_db()
        try:
            cur = conn.cursor()
            where, params = "1=1", []
            if search and search.strip():
                q = f"%{search.strip()}%"
                where = "(patient_name_canonical LIKE ? OR mobile_canonical LIKE ?)"
                params = [q, q]
            params.extend([limit, offset])
            cur.execute(
                f"""
                SELECT
                    record_no, patient_name_canonical, mobile_canonical,
                    financial_tier, action_type, action_priority_score,
                    last_payment_date_raw, lifetime_net_received, followup_recommendation
                FROM v_financial_followup_queue_contactable
                WHERE {where}
                ORDER BY action_priority_score DESC, lifetime_net_received DESC
                LIMIT ? OFFSET ?
                """,
                params,
            )
            rows = cur.fetchall()
            return {"data": [dict(r) for r in rows], "count": len(rows)}
        finally:
            conn.close()
    except sqlite3.OperationalError as e:
        logger.warning("financial followup/contactable: %s", e)
        raise HTTPException(
            status_code=503,
            detail=f"View v_financial_followup_queue_contactable not available: {e}",
        )


# ── Followup daily balanced ───────────────────────────────────────────────────
@router.get("/followup/daily")
def get_followup_daily(
    limit: int = Query(500, ge=1, le=2000, description="Max rows"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    search: Optional[str] = Query(None, description="Search name or mobile"),
):
    """
    Read from v_financial_followup_daily_balanced.

    Returns: patient_name_canonical, mobile_canonical, financial_tier, action_type,
    action_priority_score, last_payment_date_raw, lifetime_net_received, followup_recommendation.
    """
    try:
        conn = get_financial_db()
        try:
            cur = conn.cursor()
            where, params = "1=1", []
            if search and search.strip():
                q = f"%{search.strip()}%"
                where = "(patient_name_canonical LIKE ? OR mobile_canonical LIKE ?)"
                params = [q, q]
            params.extend([limit, offset])
            cur.execute(
                f"""
                SELECT
                    record_no, patient_name_canonical, mobile_canonical,
                    financial_tier, action_type, action_priority_score,
                    last_payment_date_raw, lifetime_net_received, followup_recommendation
                FROM v_financial_followup_daily_balanced
                WHERE {where}
                ORDER BY action_priority_score DESC, lifetime_net_received DESC
                LIMIT ? OFFSET ?
                """,
                params,
            )
            rows = cur.fetchall()
            return {"data": [dict(r) for r in rows], "count": len(rows)}
        finally:
            conn.close()
    except sqlite3.OperationalError as e:
        logger.warning("financial followup/daily: %s", e)
        raise HTTPException(
            status_code=503,
            detail=f"View v_financial_followup_daily_balanced not available: {e}",
        )


# ── Scheduling top 300 ───────────────────────────────────────────────────────
@router.get("/scheduling/top300")
def get_scheduling_top300(
    limit: int = Query(300, ge=1, le=500, description="Max rows (default 300)"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    search: Optional[str] = Query(None, description="Search name or mobile"),
):
    """
    Read from v_financial_scheduling_queue_top300.

    Returns: patient_name_canonical, mobile_canonical, financial_tier, action_type,
    scheduling_priority_score, scheduling_band, lifetime_net_received, last_payment_date_raw.
    """
    try:
        conn = get_financial_db()
        try:
            cur = conn.cursor()
            where, params = "1=1", []
            if search and search.strip():
                q = f"%{search.strip()}%"
                where = "(patient_name_canonical LIKE ? OR mobile_canonical LIKE ?)"
                params = [q, q]
            params.extend([limit, offset])
            cur.execute(
                f"""
                SELECT
                    patient_name_canonical, mobile_canonical, financial_tier,
                    action_type, scheduling_priority_score, scheduling_band,
                    lifetime_net_received, last_payment_date_raw, record_no
                FROM v_financial_scheduling_queue_top300
                WHERE {where}
                ORDER BY scheduling_priority_score DESC, lifetime_net_received DESC
                LIMIT ? OFFSET ?
                """,
                params,
            )
            rows = cur.fetchall()
            return {"data": [dict(r) for r in rows], "count": len(rows)}
        finally:
            conn.close()
    except sqlite3.OperationalError as e:
        logger.warning("financial scheduling/top300: %s", e)
        raise HTTPException(
            status_code=503,
            detail=f"View v_financial_scheduling_queue_top300 not available: {e}",
        )


# ── Dashboard summary ────────────────────────────────────────────────────────
@router.get("/dashboard/summary")
def get_dashboard_summary():
    """
    Return summary counts for the operational dashboard.

    Returns: total_followup_contactable, total_daily_balanced, total_scheduling_top300,
    critical_priority_count, high_priority_count, medium_priority_count.
    """
    conn = get_financial_db()
    try:
        cur = conn.cursor()
        result = {}
        # Total counts from views
        for view, key in [
            ("v_financial_followup_queue_contactable", "total_followup_contactable"),
            ("v_financial_followup_daily_balanced", "total_daily_balanced"),
            ("v_financial_scheduling_queue_top300", "total_scheduling_top300"),
        ]:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {view}")
                result[key] = cur.fetchone()[0]
            except sqlite3.OperationalError:
                result[key] = 0

        # Priority band counts from top300
        for band, key in [
            ("CRITICAL_PRIORITY", "critical_priority_count"),
            ("HIGH_PRIORITY", "high_priority_count"),
            ("MEDIUM_PRIORITY", "medium_priority_count"),
        ]:
            try:
                cur.execute(
                    """
                    SELECT COUNT(*) FROM v_financial_scheduling_queue_top300
                    WHERE scheduling_band = ?
                    """,
                    (band,),
                )
                result[key] = cur.fetchone()[0]
            except sqlite3.OperationalError:
                result[key] = 0
        return result
    finally:
        conn.close()


# ── Scheduling priority (v_financial_scheduling_priority) ─────────────────────
@router.get("/scheduling/priority")
def get_scheduling_priority(
    limit: int = Query(500, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    scheduling_band: Optional[str] = Query(None, description="Filter by scheduling_band"),
    action_type: Optional[str] = Query(None, description="Filter by action_type"),
    financial_tier: Optional[str] = Query(None, description="Filter by financial_tier"),
):
    """
    Read from v_financial_scheduling_priority with optional filters.

    Returns: patient_name_canonical, mobile_canonical, financial_tier, action_type,
    scheduling_priority_score, scheduling_band, lifetime_net_received, last_payment_date_raw.
    """
    try:
        conn = get_financial_db()
        try:
            cur = conn.cursor()
            where_parts = []
            params = []
            if scheduling_band:
                where_parts.append("scheduling_band = ?")
                params.append(scheduling_band)
            if action_type:
                where_parts.append("action_type = ?")
                params.append(action_type)
            if financial_tier:
                where_parts.append("financial_tier = ?")
                params.append(financial_tier)
            where_sql = " AND ".join(where_parts) if where_parts else "1=1"
            params.extend([limit, offset])
            cur.execute(
                f"""
                SELECT
                    record_no, patient_name_canonical, mobile_canonical,
                    financial_tier, action_type, scheduling_band,
                    scheduling_priority_score, lifetime_net_received, last_payment_date_raw
                FROM v_financial_scheduling_priority
                WHERE {where_sql}
                ORDER BY scheduling_priority_score DESC, lifetime_net_received DESC
                LIMIT ? OFFSET ?
                """,
                params,
            )
            rows = cur.fetchall()
            return {"data": [dict(r) for r in rows], "count": len(rows)}
        finally:
            conn.close()
    except sqlite3.OperationalError as e:
        logger.warning("financial scheduling/priority: %s", e)
        raise HTTPException(
            status_code=503,
            detail=f"View v_financial_scheduling_priority not available: {e}",
        )


# ── Patient financial lookup (for new appointment) ───────────────────────────
@router.get("/patient-lookup")
def get_patient_financial_lookup(
    mobile: Optional[str] = Query(None),
    record_no: Optional[str] = Query(None),
):
    """
    Lookup financial tier, action_type, scheduling_priority_score for a patient
    by mobile or record_no. Searches top300 and daily balanced.
    """
    if not mobile and not record_no:
        return {"found": False, "data": None}
    conn = get_financial_db()
    try:
        cur = conn.cursor()
        row = None
        if mobile:
            mobile_clean = "".join(c for c in str(mobile) if c.isdigit())
            if len(mobile_clean) >= 10:
                cur.execute(
                    """
                    SELECT patient_name_canonical, mobile_canonical, financial_tier,
                           action_type, scheduling_priority_score, scheduling_band,
                           lifetime_net_received, record_no
                    FROM v_financial_scheduling_queue_top300
                    WHERE REPLACE(REPLACE(mobile_canonical,' ',''),'-','') LIKE ?
                    LIMIT 1
                    """,
                    (f"%{mobile_clean[-10:]}%",),
                )
                row = cur.fetchone()
                if not row:
                    cur.execute(
                        """
                        SELECT patient_name_canonical, mobile_canonical, financial_tier,
                               action_type, action_priority_score, NULL as scheduling_priority_score,
                               lifetime_net_received, record_no
                        FROM v_financial_followup_daily_balanced
                        WHERE REPLACE(REPLACE(mobile_canonical,' ',''),'-','') LIKE ?
                        LIMIT 1
                        """,
                        (f"%{mobile_clean[-10:]}%",),
                    )
                    row = cur.fetchone()
        elif record_no:
            cur.execute(
                """
                SELECT patient_name_canonical, mobile_canonical, financial_tier,
                       action_type, scheduling_priority_score, scheduling_band,
                       lifetime_net_received, record_no
                FROM v_financial_scheduling_queue_top300
                WHERE record_no = ?
                LIMIT 1
                """,
                (str(record_no),),
            )
            row = cur.fetchone()
        if row:
            return {"found": True, "data": dict(row)}
        return {"found": False, "data": None}
    finally:
        conn.close()


# ── Test / status route ──────────────────────────────────────────────────────
@router.get("/status")
def financial_status():
    """
    Verify that the financial operational views exist and return counts.
    Useful for API smoke tests.
    """
    conn = get_financial_db()
    try:
        cur = conn.cursor()
        result = {
            "db_path": os.path.abspath(DB_PATH),
            "views": {},
        }
        for view in [
            "v_financial_followup_queue_contactable",
            "v_financial_followup_daily_balanced",
            "v_financial_scheduling_queue_top300",
        ]:
            try:
                cur.execute(f"SELECT COUNT(*) AS c FROM {view}")
                count = cur.fetchone()[0]
                result["views"][view] = {"count": count, "ok": True}
            except sqlite3.OperationalError as e:
                result["views"][view] = {"ok": False, "error": str(e)}
        return result
    finally:
        conn.close()
