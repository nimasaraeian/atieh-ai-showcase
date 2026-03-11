# -*- coding: utf-8 -*-
"""
Manager dashboard API – financial overview, tier distribution, top patients, decision logs.
"""
import os
import sqlite3
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query

from app.security.roles import serialize_manager_patient

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("FINANCIAL_DB_PATH") or (
    "atieh_clinic_working.db"
    if os.path.exists("atieh_clinic_working.db")
    else "atieh_clinic.db"
)

router = APIRouter(prefix="/api/manager", tags=["Manager"])


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name = ?",
        (name,),
    )
    return cur.fetchone() is not None


@router.get("/dashboard/summary")
def get_dashboard_summary() -> Dict[str, Any]:
    """
    Tier distribution and patient counts for manager dashboard.
    Uses financial_identity_profile; falls back gracefully if not available.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        result: Dict[str, Any] = {
            "total_patients": 0,
            "vip_patients": 0,
            "high_patients": 0,
            "medium_patients": 0,
            "low_patients": 0,
        }

        if not _table_exists(conn, "financial_identity_profile"):
            return result

        cur.execute("SELECT COUNT(*) FROM financial_identity_profile")
        result["total_patients"] = cur.fetchone()[0]

        for tier, key in [
            ("VIP", "vip_patients"),
            ("HIGH", "high_patients"),
            ("MEDIUM", "medium_patients"),
            ("LOW", "low_patients"),
        ]:
            try:
                cur.execute(
                    "SELECT COUNT(*) FROM financial_identity_profile WHERE financial_tier = ?",
                    (tier,),
                )
                result[key] = cur.fetchone()[0]
            except sqlite3.OperationalError:
                result[key] = 0

        return result
    finally:
        conn.close()


@router.get("/patients/top-value")
def get_top_value_patients(limit: int = 20, tier: str = Query(None)) -> Dict[str, Any]:
    """
    Top patients by lifetime payment. Filter by tier if provided.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()

        view_ok = _table_exists(conn, "v_financial_identity_profile")
        table_ok = _table_exists(conn, "financial_identity_profile")

        tier_filter = " AND financial_tier = ?" if (tier and tier.strip()) else ""
        params = [limit] if not (tier and tier.strip()) else [tier.strip(), limit]

        if view_ok:
            sql = f"""
                SELECT
                    record_no,
                    patient_name_canonical AS patient_name,
                    mobile_canonical AS mobile,
                    financial_tier,
                    lifetime_net_received AS lifetime_payment,
                    last_payment_date_raw AS last_visit_date
                FROM v_financial_identity_profile
                WHERE 1=1{tier_filter}
                ORDER BY COALESCE(lifetime_net_received, 0) DESC
                LIMIT ?
            """
        elif table_ok:
            sql = f"""
                SELECT
                    record_no,
                    NULL AS patient_name,
                    NULL AS mobile,
                    financial_tier,
                    lifetime_net_received AS lifetime_payment,
                    last_payment_date_raw AS last_visit_date
                FROM financial_identity_profile
                WHERE 1=1{tier_filter}
                ORDER BY COALESCE(lifetime_net_received, 0) DESC
                LIMIT ?
            """
        else:
            return {"count": 0, "data": []}

        cur.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]

        # Map to manager serialization format
        def _row(r):
            d = dict(r)
            d["lifetime_payment"] = d.get("lifetime_payment") or d.get("lifetime_net_received")
            d["last_payment_date_raw"] = d.get("last_visit_date")
            return d

        data = [serialize_manager_patient(_row(r)) for r in rows]

        return {"count": len(data), "data": data}
    except sqlite3.OperationalError as e:
        logger.warning("manager top-value: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        conn.close()


@router.get("/decision-logs")
def get_decision_logs(limit: int = 20) -> Dict[str, Any]:
    """
    Latest decision log entries.
    Uses decision_logs table (id, created_at, decision_type, entity_type, entity_id, etc.)
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()

        if not _table_exists(conn, "decision_logs"):
            return {"count": 0, "data": []}

        cur.execute(
            """
            SELECT
                decision_type AS operation,
                entity_type,
                entity_id,
                decision_value,
                reason,
                created_at AS timestamp,
                context_json
            FROM decision_logs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()

        data: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            # Map to expected shape: operation, rows_affected, timestamp
            row = {
                "operation": d.get("operation") or d.get("decision_type") or "-",
                "rows_affected": None,  # schema has no rows_affected; context_json may hold it
                "timestamp": d.get("timestamp") or "-",
            }
            if d.get("context_json"):
                try:
                    import json
                    ctx = json.loads(d["context_json"])
                    row["rows_affected"] = ctx.get("rows_affected") or ctx.get("count")
                except Exception:
                    pass
            data.append(row)

        return {"count": len(data), "data": data}
    except sqlite3.OperationalError as e:
        logger.warning("manager decision-logs: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        conn.close()
