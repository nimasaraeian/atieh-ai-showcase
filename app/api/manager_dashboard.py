# -*- coding: utf-8 -*-
"""
Manager dashboard API – real metrics from SQLite database.

All endpoints query atieh_clinic.db (or FINANCIAL_DB_PATH).
Uses: patients, appointments, payments_clean, financial_identity_profile.

CURRENCY UNIT: All monetary values (net_received, lifetime_net_received) are in تومان (Toman).
"""

import os
import sqlite3
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query, Depends

from app.security.rbac import require_roles

logger = logging.getLogger(__name__)


def _parse_date(s: str) -> str:
    """Return date string YYYY-MM-DD for SQLite, or None if invalid."""
    if not s or not s.strip():
        return None
    return s.strip()[:10]

DB_PATH = os.environ.get("FINANCIAL_DB_PATH") or (
    "atieh_clinic_working.db"
    if os.path.exists("atieh_clinic_working.db")
    else "atieh_clinic.db"
)

router = APIRouter(
    prefix="/api/manager",
    tags=["Manager Dashboard"],
    dependencies=[Depends(require_roles("clinic_manager"))],
)


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


def _column_exists(conn: sqlite3.Connection, table: str, col: str) -> bool:
    cur = conn.execute("PRAGMA table_info(" + table + ")")
    return any(r[1] == col for r in cur.fetchall())


def _service_filter_clause(conn: sqlite3.Connection, service: str, use_clean: bool) -> tuple:
    """
    Return (sql_fragment, params) for filtering by service.
    If use_clean and service_dim populated: filter by clean_service_category via join.
    Else: filter by raw raw_text_service or treatment_type.
    """
    if not service or not service.strip():
        return "", []
    svc = service.strip()
    if use_clean and _table_exists(conn, "service_dim"):
        cur = conn.execute("SELECT COUNT(*) FROM service_dim WHERE is_noise = 0")
        if cur.fetchone()[0] > 0:
            return (
                " AND id IN (SELECT a2.id FROM appointments a2 "
                "INNER JOIN service_dim sd ON sd.raw_service_text = TRIM(COALESCE(a2.raw_text_service,'')) "
                "WHERE sd.clean_service_category = ?)",
                [svc],
            )
    if _column_exists(conn, "appointments", "raw_text_service"):
        return (" AND LOWER(TRIM(COALESCE(raw_text_service,''))) = LOWER(TRIM(?))", [svc])
    if _column_exists(conn, "appointments", "treatment_type"):
        return (" AND LOWER(TRIM(COALESCE(treatment_type,''))) = LOWER(TRIM(?))", [svc])
    return "", []


def _doctor_filter_clause(conn: sqlite3.Connection, doctor: str, use_clean: bool) -> tuple:
    """Return (sql_fragment, params) for filtering by doctor. Uses doctor_dim when available."""
    if not doctor or not doctor.strip():
        return "", []
    doc = doctor.strip()
    if use_clean and _table_exists(conn, "doctor_dim"):
        cur = conn.execute("SELECT COUNT(*) FROM doctor_dim")
        if cur.fetchone()[0] > 0:
            return (
                " AND id IN (SELECT a2.id FROM appointments a2 "
                "INNER JOIN doctor_dim dd ON dd.raw_doctor_text = TRIM(COALESCE(a2.raw_text_doctor,'')) "
                "WHERE dd.clean_doctor_name = ?)",
                [doc],
            )
    if _column_exists(conn, "appointments", "raw_text_doctor"):
        return (" AND LOWER(TRIM(COALESCE(raw_text_doctor,''))) = LOWER(TRIM(?))", [doc])
    if _column_exists(conn, "appointments", "doctor_name"):
        return (" AND LOWER(TRIM(COALESCE(doctor_name,''))) = LOWER(TRIM(?))", [doc])
    return "", []


# ─── 0) Filter options (populate dropdowns) ─────────────────────────────────
@router.get("/filters/doctors")
def get_filter_doctors() -> Dict[str, Any]:
    """Distinct clean doctor names from doctor_dim (fallback: raw_text_doctor)."""
    conn = _get_conn()
    try:
        if _table_exists(conn, "doctor_dim"):
            cur = conn.execute(
                "SELECT DISTINCT clean_doctor_name FROM doctor_dim "
                "WHERE clean_doctor_name IS NOT NULL AND TRIM(clean_doctor_name) != '' ORDER BY clean_doctor_name"
            )
            rows = [r[0] for r in cur.fetchall()]
            if rows:
                return {"data": rows}
        if _table_exists(conn, "appointments") and _column_exists(conn, "appointments", "raw_text_doctor"):
            cur = conn.execute(
                "SELECT DISTINCT raw_text_doctor FROM appointments WHERE raw_text_doctor IS NOT NULL AND TRIM(raw_text_doctor) != '' ORDER BY raw_text_doctor"
            )
            return {"data": [r[0] for r in cur.fetchall()]}
        if _table_exists(conn, "doctor_master"):
            cur = conn.execute("SELECT DISTINCT doctor_name FROM doctor_master WHERE doctor_name IS NOT NULL ORDER BY doctor_name")
            return {"data": [r[0] for r in cur.fetchall()]}
        return {"data": []}
    finally:
        conn.close()


@router.get("/filters/services")
def get_filter_services() -> Dict[str, Any]:
    """Distinct clean service categories from service_dim (fallback: raw_text_service/treatment_type)."""
    conn = _get_conn()
    try:
        if _table_exists(conn, "service_dim"):
            cur = conn.execute(
                "SELECT DISTINCT clean_service_category FROM service_dim "
                "WHERE is_noise = 0 AND clean_service_category IS NOT NULL AND TRIM(clean_service_category) != '' "
                "ORDER BY clean_service_category"
            )
            rows = [r[0] for r in cur.fetchall()]
            if rows:
                return {"data": rows}
        if not _table_exists(conn, "appointments"):
            return {"data": []}
        col = "raw_text_service" if _column_exists(conn, "appointments", "raw_text_service") else "treatment_type"
        if not _column_exists(conn, "appointments", col):
            return {"data": []}
        cur = conn.execute(
            f"SELECT DISTINCT {col} FROM appointments WHERE {col} IS NOT NULL AND TRIM({col}) != '' ORDER BY {col}"
        )
        return {"data": [r[0] for r in cur.fetchall()]}
    except sqlite3.OperationalError:
        return {"data": []}
    finally:
        conn.close()


@router.get("/filters/payment-types")
def get_filter_payment_types() -> Dict[str, Any]:
    """Distinct payment types from payments_clean (payer_source_norm)."""
    conn = _get_conn()
    try:
        if not _table_exists(conn, "payments_clean"):
            return {"data": []}
        cur = conn.execute(
            "SELECT DISTINCT payer_source_norm FROM payments_clean WHERE payer_source_norm IS NOT NULL AND TRIM(payer_source_norm) != '' ORDER BY payer_source_norm"
        )
        return {"data": [r[0] for r in cur.fetchall()]}
    finally:
        conn.close()


@router.get("/filters/patient-tiers")
def get_filter_patient_tiers() -> Dict[str, Any]:
    """Distinct tiers from financial_identity_profile."""
    conn = _get_conn()
    try:
        if not _table_exists(conn, "financial_identity_profile"):
            return {"data": []}
        cur = conn.execute(
            "SELECT DISTINCT financial_tier FROM financial_identity_profile WHERE financial_tier IN ('VIP','HIGH','MEDIUM','LOW') ORDER BY CASE financial_tier WHEN 'VIP' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END"
        )
        return {"data": [r[0] for r in cur.fetchall()]}
    finally:
        conn.close()


# ─── 1) Total Patients ─────────────────────────────────────────────────────
@router.get("/total-patients")
def get_total_patients(tier: str = Query(None)) -> Dict[str, Any]:
    """KPI: Total patient records. Filter by tier uses financial_identity_profile."""
    conn = _get_conn()
    try:
        if tier and _table_exists(conn, "financial_identity_profile"):
            cur = conn.execute(
                "SELECT COUNT(*) AS c FROM financial_identity_profile WHERE financial_tier = ?",
                (tier.strip(),),
            )
            return {"total_patients": cur.fetchone()[0]}
        if not _table_exists(conn, "patients"):
            return {"total_patients": 0}
        cur = conn.execute("SELECT COUNT(*) AS c FROM patients")
        return {"total_patients": cur.fetchone()[0]}
    except sqlite3.OperationalError as e:
        logger.warning("total-patients: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        conn.close()


# ─── 2) Total Transactions ─────────────────────────────────────────────────
@router.get("/total-transactions")
def get_total_transactions(
    start_date: str = Query(None), end_date: str = Query(None),
    payment: str = Query(None),
) -> Dict[str, Any]:
    """KPI: Payment rows. Filters: start_date, end_date, payment (payer_source_norm)."""
    conn = _get_conn()
    try:
        tbl = "payments_clean" if _table_exists(conn, "payments_clean") else "payments"
        if not _table_exists(conn, tbl):
            return {"total_transactions": 0}
        date_col = "COALESCE(SUBSTR(appointment_date_raw, 1, 10), SUBSTR(loaded_at, 1, 10))" if tbl == "payments_clean" else "date(created_at)"
        wh, params = [], []
        if _parse_date(start_date):
            wh.append(f"{date_col} >= ?")
            params.append(_parse_date(start_date))
        if _parse_date(end_date):
            wh.append(f"{date_col} <= ?")
            params.append(_parse_date(end_date))
        if payment and tbl == "payments_clean":
            wh.append("LOWER(TRIM(payer_source_norm)) = LOWER(TRIM(?))")
            params.append(payment)
        sql = f"SELECT COUNT(*) AS c FROM {tbl}" + (" WHERE " + " AND ".join(wh) if wh else "")
        cur = conn.execute(sql, params)
        return {"total_transactions": cur.fetchone()[0]}
    except sqlite3.OperationalError as e:
        logger.warning("total-transactions: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        conn.close()


# ─── 3) Total Revenue ──────────────────────────────────────────────────────
@router.get("/total-revenue")
def get_total_revenue(
    start_date: str = Query(None), end_date: str = Query(None),
    payment: str = Query(None),
) -> Dict[str, Any]:
    """KPI: Sum of net_received. Filters: start_date, end_date, payment."""
    conn = _get_conn()
    try:
        if _table_exists(conn, "payments_clean"):
            date_col = "COALESCE(SUBSTR(appointment_date_raw, 1, 10), SUBSTR(loaded_at, 1, 10))"
            wh, params = [], []
            if _parse_date(start_date):
                wh.append(f"{date_col} >= ?")
                params.append(_parse_date(start_date))
            if _parse_date(end_date):
                wh.append(f"{date_col} <= ?")
                params.append(_parse_date(end_date))
            if payment:
                wh.append("LOWER(TRIM(payer_source_norm)) = LOWER(TRIM(?))")
                params.append(payment)
            sql = "SELECT COALESCE(SUM(net_received), 0) AS total FROM payments_clean" + (" WHERE " + " AND ".join(wh) if wh else "")
            cur = conn.execute(sql, params)
        elif _table_exists(conn, "payments"):
            cur = conn.execute("SELECT COALESCE(SUM(amount), 0) AS total FROM payments")
        else:
            return {"total_revenue": 0}
        return {"total_revenue": cur.fetchone()[0]}
    except sqlite3.OperationalError as e:
        logger.warning("total-revenue: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        conn.close()


# ─── 4) VIP Patients ───────────────────────────────────────────────────────
@router.get("/vip-patients")
def get_vip_patients() -> Dict[str, Any]:
    """SELECT COUNT(*) FROM financial_identity_profile WHERE financial_tier='VIP'"""
    conn = _get_conn()
    try:
        if not _table_exists(conn, "financial_identity_profile"):
            return {"vip_patients": 0}
        cur = conn.execute(
            "SELECT COUNT(*) AS c FROM financial_identity_profile WHERE financial_tier = 'VIP'"
        )
        return {"vip_patients": cur.fetchone()[0]}
    except sqlite3.OperationalError as e:
        logger.warning("vip-patients: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        conn.close()


# ─── 5) No-Show Rate ───────────────────────────────────────────────────────
@router.get("/no-show-rate")
def get_no_show_rate(
    start_date: str = Query(None), end_date: str = Query(None),
    doctor: str = Query(None), service: str = Query(None),
) -> Dict[str, Any]:
    """Percentage of appointments with status='no_show'. Filters: start_date, end_date, doctor, service."""
    conn = _get_conn()
    try:
        if not _table_exists(conn, "appointments"):
            return {"no_show_rate": 0}
        wh, params = [], []
        if _parse_date(start_date):
            wh.append("date(appointment_date) >= ?")
            params.append(_parse_date(start_date))
        if _parse_date(end_date):
            wh.append("date(appointment_date) <= ?")
            params.append(_parse_date(end_date))
        doc_clause, doc_params = _doctor_filter_clause(conn, doctor, use_clean=True)
        if doc_clause:
            wh.append(doc_clause.strip().lstrip("AND "))
            params.extend(doc_params)
        svc_clause, svc_params = _service_filter_clause(conn, service, use_clean=True)
        if svc_clause:
            wh.append(svc_clause.strip().lstrip("AND "))
            params.extend(svc_params)
        where = " WHERE " + " AND ".join(wh) if wh else ""
        cur = conn.execute(
            f"""
            SELECT
                CASE WHEN COUNT(*) = 0 THEN 0
                     ELSE SUM(CASE WHEN LOWER(TRIM(COALESCE(status,''))) = 'no_show' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)
                END AS rate
            FROM appointments{where}
            """,
            params,
        )
        return {"no_show_rate": round(cur.fetchone()[0], 2)}
    except sqlite3.OperationalError as e:
        logger.warning("no-show-rate: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        conn.close()


# ─── 5a) Financial Summary (today, weekly, total, debt placeholder) ─────────
@router.get("/financial-summary")
def get_financial_summary(
    start_date: str = Query(None), end_date: str = Query(None),
    payment: str = Query(None),
) -> Dict[str, Any]:
    """
    Today, weekly, total collected from payments_clean. Filters: start_date, end_date, payment.
    """
    conn = _get_conn()
    try:
        if not _table_exists(conn, "payments_clean"):
            return {
                "today_revenue": 0,
                "weekly_revenue": 0,
                "total_collected": 0,
                "outstanding_debt": 0,
            }
        cur = conn.cursor()
        date_col = "COALESCE(SUBSTR(appointment_date_raw, 1, 10), SUBSTR(loaded_at, 1, 10))"

        cur.execute(
            f"SELECT COALESCE(SUM(net_received), 0) FROM payments_clean WHERE net_received IS NOT NULL AND {date_col} = date('now')"
        )
        today_revenue = cur.fetchone()[0] or 0

        cur.execute(
            f"""
            SELECT COALESCE(SUM(net_received), 0) FROM payments_clean
            WHERE net_received IS NOT NULL AND {date_col} >= date('now', '-7 days') AND {date_col} <= date('now')
            """
        )
        weekly_revenue = cur.fetchone()[0] or 0

        total_wh = ["net_received IS NOT NULL"]
        total_params = []
        if _parse_date(start_date):
            total_wh.append(f"{date_col} >= ?")
            total_params.append(_parse_date(start_date))
        if _parse_date(end_date):
            total_wh.append(f"{date_col} <= ?")
            total_params.append(_parse_date(end_date))
        if payment:
            total_wh.append("LOWER(TRIM(payer_source_norm)) = LOWER(TRIM(?))")
            total_params.append(payment)
        cur.execute(
            f"SELECT COALESCE(SUM(net_received), 0) FROM payments_clean WHERE {' AND '.join(total_wh)}",
            total_params,
        )
        total_collected = cur.fetchone()[0] or 0
        return {
            "today_revenue": today_revenue,
            "weekly_revenue": weekly_revenue,
            "total_collected": total_collected,
            "outstanding_debt": 0,  # Schema has no debt table; show 0
        }
    except sqlite3.OperationalError as e:
        logger.warning("financial-summary: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        conn.close()


# ─── 5b) Active Doctors ────────────────────────────────────────────────────
@router.get("/active-doctors")
def get_active_doctors(
    start_date: str = Query(None), end_date: str = Query(None),
) -> Dict[str, Any]:
    """COUNT from doctor_master; fallback to COUNT(DISTINCT clean_doctor_name) from doctor_dim+appointments."""
    conn = _get_conn()
    try:
        if _table_exists(conn, "doctor_master"):
            cur = conn.execute("SELECT COUNT(*) AS c FROM doctor_master")
            cnt = cur.fetchone()[0]
            if cnt > 0:
                return {"active_doctors": cnt}
        if _table_exists(conn, "doctor_dim") and _table_exists(conn, "appointments"):
            wh, params = [], []
            if _parse_date(start_date):
                wh.append("date(a.appointment_date) >= ?")
                params.append(_parse_date(start_date))
            if _parse_date(end_date):
                wh.append("date(a.appointment_date) <= ?")
                params.append(_parse_date(end_date))
            where = (" AND " + " AND ".join(wh)) if wh else ""
            cur = conn.execute(
                f"""
                SELECT COUNT(DISTINCT dd.clean_doctor_name) AS c
                FROM appointments a
                INNER JOIN doctor_dim dd ON dd.raw_doctor_text = TRIM(COALESCE(a.raw_text_doctor,''))
                WHERE dd.clean_doctor_name IS NOT NULL AND TRIM(dd.clean_doctor_name) != ''{where}
                """,
                params,
            )
            return {"active_doctors": cur.fetchone()[0] or 0}
        if _table_exists(conn, "appointments") and _column_exists(conn, "appointments", "raw_text_doctor"):
            cur = conn.execute(
                "SELECT COUNT(DISTINCT raw_text_doctor) FROM appointments WHERE raw_text_doctor IS NOT NULL AND TRIM(raw_text_doctor) != ''"
            )
            return {"active_doctors": cur.fetchone()[0] or 0}
        return {"active_doctors": 0}
    except sqlite3.OperationalError as e:
        logger.warning("active-doctors: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        conn.close()


# ─── 5c) Transaction Stats (payments_clean has no status; all rows = received) ─
@router.get("/transaction-stats")
def get_transaction_stats(
    start_date: str = Query(None), end_date: str = Query(None),
    payment: str = Query(None),
) -> Dict[str, Any]:
    """Transaction stats. Filters: start_date, end_date, payment."""
    conn = _get_conn()
    try:
        tbl = "payments_clean" if _table_exists(conn, "payments_clean") else None
        if not tbl:
            return {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "cash_pct": 0,
                "insurance_pct": 0,
                "avg_value": 0,
            }
        cur = conn.cursor()
        date_col = "COALESCE(SUBSTR(appointment_date_raw, 1, 10), SUBSTR(loaded_at, 1, 10))"
        wh, params = [], []
        if _parse_date(start_date):
            wh.append(f"{date_col} >= ?")
            params.append(_parse_date(start_date))
        if _parse_date(end_date):
            wh.append(f"{date_col} <= ?")
            params.append(_parse_date(end_date))
        if payment:
            wh.append("LOWER(TRIM(payer_source_norm)) = LOWER(TRIM(?))")
            params.append(payment)
        where = " WHERE " + " AND ".join(wh) if wh else ""
        cur.execute(f"SELECT COUNT(*) AS c, COALESCE(SUM(net_received), 0) AS s FROM {tbl}{where}", params)
        row = cur.fetchone()
        total = row[0] or 0
        total_sum = row[1] or 0
        sub_wh = ["payer_source_norm IS NOT NULL AND TRIM(payer_source_norm) != ''"] + wh
        cur.execute(
            f"""
            SELECT LOWER(TRIM(payer_source_norm)) AS norm, COUNT(*) FROM {tbl}
            WHERE {" AND ".join(sub_wh)}
            GROUP BY norm
            """,
            params,
        )
        by_source = {r[0] or "": r[1] for r in cur.fetchall()}
        cash_count = by_source.get("cash", 0) + by_source.get("card", 0)
        ins_count = by_source.get("insurance", 0)
        denom = cash_count + ins_count or 1
        cash_pct = round(cash_count * 100.0 / denom, 0)
        insurance_pct = round(ins_count * 100.0 / denom, 0)
        avg_value = round(total_sum / total, 0) if total else 0
        return {
            "total": total,
            "successful": total,  # All payments_clean rows = received
            "failed": 0,  # No status in schema
            "cash_pct": int(cash_pct),
            "insurance_pct": int(insurance_pct),
            "avg_value": avg_value,
        }
    except sqlite3.OperationalError as e:
        logger.warning("transaction-stats: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        conn.close()


# ─── 6) Doctor Utilization ─────────────────────────────────────────────────
@router.get("/doctor-utilization")
def get_doctor_utilization(
    start_date: str = Query(None), end_date: str = Query(None),
    doctor: str = Query(None), service: str = Query(None),
) -> Dict[str, Any]:
    """Percentage of appointments with status='completed'. Filters: start_date, end_date, doctor, service."""
    conn = _get_conn()
    try:
        if not _table_exists(conn, "appointments"):
            return {"utilization": 0}
        wh, params = [], []
        if _parse_date(start_date):
            wh.append("date(appointment_date) >= ?")
            params.append(_parse_date(start_date))
        if _parse_date(end_date):
            wh.append("date(appointment_date) <= ?")
            params.append(_parse_date(end_date))
        doc_clause, doc_params = _doctor_filter_clause(conn, doctor, use_clean=True)
        if doc_clause:
            wh.append(doc_clause.strip().lstrip("AND "))
            params.extend(doc_params)
        svc_clause, svc_params = _service_filter_clause(conn, service, use_clean=True)
        if svc_clause:
            wh.append(svc_clause.strip().lstrip("AND "))
            params.extend(svc_params)
        where = " WHERE " + " AND ".join(wh) if wh else ""
        cur = conn.execute(
            f"""
            SELECT
                CASE WHEN COUNT(*) = 0 THEN 0
                     ELSE SUM(CASE WHEN LOWER(TRIM(COALESCE(status,''))) = 'completed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)
                END AS util
            FROM appointments{where}
            """,
            params,
        )
        return {"utilization": round(cur.fetchone()[0], 2)}
    except sqlite3.OperationalError as e:
        logger.warning("doctor-utilization: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        conn.close()


# ─── 7) Payment Method Distribution ────────────────────────────────────────
@router.get("/payment-distribution")
def get_payment_distribution(
    start_date: str = Query(None), end_date: str = Query(None),
) -> Dict[str, Any]:
    """Payment distribution. Filters: start_date, end_date."""
    conn = _get_conn()
    try:
        if not _table_exists(conn, "payments_clean"):
            return {"data": []}
        date_col = "COALESCE(SUBSTR(appointment_date_raw, 1, 10), SUBSTR(loaded_at, 1, 10))"
        wh, params = ["payer_source_norm IS NOT NULL AND TRIM(payer_source_norm) != ''"], []
        if _parse_date(start_date):
            wh.append(f"{date_col} >= ?")
            params.append(_parse_date(start_date))
        if _parse_date(end_date):
            wh.append(f"{date_col} <= ?")
            params.append(_parse_date(end_date))
        sql = f"""
            SELECT payer_source_norm AS payment_method, COUNT(*) AS count
            FROM payments_clean
            WHERE {" AND ".join(wh)}
            GROUP BY payer_source_norm
            ORDER BY count DESC
        """
        cur = conn.execute(sql, params)
        rows = [{"payment_method": r[0], "count": r[1]} for r in cur.fetchall()]
        total = sum(r["count"] for r in rows)
        for r in rows:
            r["percent"] = round(r["count"] * 100.0 / total, 1) if total else 0
        return {"data": rows}
    except sqlite3.OperationalError as e:
        logger.warning("payment-distribution: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        conn.close()


# ─── 7b) Tier Distribution ─────────────────────────────────────────────────
@router.get("/tier-distribution")
def get_tier_distribution(tier: str = Query(None)) -> Dict[str, Any]:
    """Tier counts. Optional filter: tier (single tier only)."""
    conn = _get_conn()
    try:
        if not _table_exists(conn, "financial_identity_profile"):
            return {"data": []}
        cur = conn.cursor()
        tier_wh = " AND financial_tier = ?" if (tier and tier.strip()) else ""
        tier_param = [tier.strip()] if (tier and tier.strip()) else []
        cur.execute(
            f"""
            SELECT financial_tier, COUNT(*) AS cnt
            FROM financial_identity_profile
            WHERE financial_tier IN ('VIP','HIGH','MEDIUM','LOW'){tier_wh}
            GROUP BY financial_tier
            ORDER BY CASE financial_tier WHEN 'VIP' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END
            """,
            tier_param,
        )
        colors = {"VIP": "#f59e0b", "HIGH": "#10b981", "MEDIUM": "#06b6d4", "LOW": "#64748b"}
        data = [{"name": r[0], "value": r[1], "color": colors.get(r[0], "#64748b")} for r in cur.fetchall()]
        return {"data": data}
    except sqlite3.OperationalError as e:
        logger.warning("tier-distribution: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        conn.close()


# ─── 7c) Transaction Trend ──────────────────────────────────────────────────
@router.get("/transaction-trend")
def get_transaction_trend(
    limit: int = 30,
    start_date: str = Query(None), end_date: str = Query(None),
    payment: str = Query(None),
) -> Dict[str, Any]:
    """Daily transaction count. Filters: start_date, end_date, payment."""
    conn = _get_conn()
    try:
        if not _table_exists(conn, "payments_clean"):
            return {"data": []}
        date_col = "COALESCE(SUBSTR(appointment_date_raw, 1, 10), SUBSTR(loaded_at, 1, 10), date('now'))"
        wh, params = [], [limit]
        if _parse_date(start_date):
            wh.append(f"{date_col} >= ?")
            params.insert(-1, _parse_date(start_date))
        if _parse_date(end_date):
            wh.append(f"{date_col} <= ?")
            params.insert(-1, _parse_date(end_date))
        if payment:
            wh.append("LOWER(TRIM(payer_source_norm)) = LOWER(TRIM(?))")
            params.insert(-1, payment)
        where = " WHERE " + " AND ".join(wh) if wh else ""
        cur = conn.execute(
            f"""
            SELECT {date_col} AS day, COUNT(*) AS count
            FROM payments_clean{where}
            GROUP BY day
            ORDER BY day DESC
            LIMIT ?
            """,
            params,
        )
        rows = [{"day": r[0], "count": r[1]} for r in cur.fetchall()]
        rows.reverse()
        return {"data": rows}
    except sqlite3.OperationalError as e:
        logger.warning("transaction-trend: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        conn.close()


# ─── 7d) Top Services by Count ──────────────────────────────────────────────
@router.get("/top-services")
def get_top_services(
    limit: int = 15,
    start_date: str = Query(None), end_date: str = Query(None),
) -> Dict[str, Any]:
    """Top service categories by appointment count. Uses clean_service_category when service_dim exists."""
    conn = _get_conn()
    try:
        if not _table_exists(conn, "appointments"):
            return {"data": []}
        wh, params = [], [limit]
        if _parse_date(start_date):
            wh.append("date(a.appointment_date) >= ?")
            params.insert(-1, _parse_date(start_date))
        if _parse_date(end_date):
            wh.append("date(a.appointment_date) <= ?")
            params.insert(-1, _parse_date(end_date))
        where_extra = (" AND " + " AND ".join(wh)) if wh else ""
        if _table_exists(conn, "service_dim"):
            sql = f"""
                SELECT COALESCE(sd.clean_service_category, 'سایر') AS service, COUNT(*) AS count
                FROM appointments a
                LEFT JOIN service_dim sd ON sd.raw_service_text = TRIM(COALESCE(a.raw_text_service,''))
                WHERE (sd.is_noise = 0 OR sd.raw_service_text IS NULL){where_extra}
                GROUP BY service
                ORDER BY count DESC
                LIMIT ?
            """
        else:
            col = "raw_text_service" if _column_exists(conn, "appointments", "raw_text_service") else "treatment_type"
            if not _column_exists(conn, "appointments", col):
                return {"data": []}
            sql = f"""
                SELECT COALESCE({col}, 'سایر') AS service, COUNT(*) AS count
                FROM appointments a
                WHERE {col} IS NOT NULL AND TRIM({col}) != ''{where_extra}
                GROUP BY service
                ORDER BY count DESC
                LIMIT ?
            """
        cur = conn.execute(sql, params)
        rows = cur.fetchall()
        return {"data": [{"service": r[0], "count": r[1]} for r in rows]}
    except sqlite3.OperationalError as e:
        logger.warning("top-services: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        conn.close()


# ─── 7d2) Revenue by Doctor ─────────────────────────────────────────────────
@router.get("/revenue-by-doctor")
def get_revenue_by_doctor(
    limit: int = 15,
    start_date: str = Query(None), end_date: str = Query(None),
    payment: str = Query(None),
) -> Dict[str, Any]:
    """Revenue grouped by clean doctor name. Joins payments to appointments via patient_id+date. Uses doctor_dim when available."""
    conn = _get_conn()
    try:
        if not _table_exists(conn, "payments_clean") or not _table_exists(conn, "appointments"):
            return {"data": []}
        date_col = "COALESCE(SUBSTR(p.appointment_date_raw, 1, 10), SUBSTR(p.loaded_at, 1, 10))"
        wh, params = ["p.patient_id IS NOT NULL", "p.net_received IS NOT NULL"], [limit]
        if _parse_date(start_date):
            wh.append(f"{date_col} >= ?")
            params.insert(-1, _parse_date(start_date))
        if _parse_date(end_date):
            wh.append(f"{date_col} <= ?")
            params.insert(-1, _parse_date(end_date))
        if payment:
            wh.append("LOWER(TRIM(p.payer_source_norm)) = LOWER(TRIM(?))")
            params.insert(-1, payment)
        doc_expr = "COALESCE(dd.clean_doctor_name, TRIM(COALESCE(a.raw_text_doctor,'')))"
        join_dd = ""
        if _table_exists(conn, "doctor_dim"):
            join_dd = "LEFT JOIN doctor_dim dd ON dd.raw_doctor_text = TRIM(COALESCE(a.raw_text_doctor,''))"
        else:
            doc_expr = "TRIM(COALESCE(a.raw_text_doctor, ''))"
        sql = f"""
            SELECT {doc_expr} AS doctor_name, COALESCE(SUM(p.net_received), 0) AS revenue, COUNT(DISTINCT p.payment_id) AS txn_count
            FROM payments_clean p
            INNER JOIN appointments a ON a.patient_id = p.patient_id AND date(a.appointment_date) = date({date_col})
            {join_dd}
            WHERE {" AND ".join(wh)}
            GROUP BY doctor_name
            HAVING doctor_name IS NOT NULL AND TRIM(doctor_name) != ''
            ORDER BY revenue DESC
            LIMIT ?
        """
        cur = conn.execute(sql, params)
        rows = cur.fetchall()
        return {"data": [{"doctor_name": r[0], "revenue": r[1], "txn_count": r[2]} for r in rows]}
    except sqlite3.OperationalError as e:
        logger.warning("revenue-by-doctor: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        conn.close()


# ─── 7d3) Doctor Workload (appointment volume per doctor) ────────────────────
@router.get("/doctor-workload")
def get_doctor_workload(
    limit: int = 15,
    start_date: str = Query(None), end_date: str = Query(None),
    service: str = Query(None),
) -> Dict[str, Any]:
    """Appointment count per clean doctor. Occupied = completed, scheduled, in_progress. Uses doctor_dim when available."""
    conn = _get_conn()
    try:
        if not _table_exists(conn, "appointments"):
            return {"data": []}
        doc_expr = "COALESCE(dd.clean_doctor_name, TRIM(COALESCE(a.raw_text_doctor,'')))"
        join_dd = ""
        if _table_exists(conn, "doctor_dim"):
            join_dd = "LEFT JOIN doctor_dim dd ON dd.raw_doctor_text = TRIM(COALESCE(a.raw_text_doctor,''))"
        else:
            doc_expr = "TRIM(COALESCE(a.raw_text_doctor, ''))"
        wh, params = [
            "LOWER(TRIM(COALESCE(a.status,''))) IN ('completed','scheduled','in_progress')",
        ], [limit]
        if _parse_date(start_date):
            wh.append("date(a.appointment_date) >= ?")
            params.insert(-1, _parse_date(start_date))
        if _parse_date(end_date):
            wh.append("date(a.appointment_date) <= ?")
            params.insert(-1, _parse_date(end_date))
        svc_clause, svc_params = _service_filter_clause(conn, service, use_clean=True)
        if svc_clause:
            wh.append(svc_clause.strip().lstrip("AND "))
            params.extend(svc_params)
        sql = f"""
            SELECT {doc_expr} AS doctor_name, COUNT(*) AS appointment_count
            FROM appointments a
            {join_dd}
            WHERE {" AND ".join(wh)} AND ({doc_expr} IS NOT NULL AND TRIM(COALESCE({doc_expr},'')) != '')
            GROUP BY doctor_name
            ORDER BY appointment_count DESC
            LIMIT ?
        """
        cur = conn.execute(sql, params)
        rows = cur.fetchall()
        return {"data": [{"doctor_name": r[0], "appointment_count": r[1]} for r in rows]}
    except sqlite3.OperationalError as e:
        logger.warning("doctor-workload: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        conn.close()


# ─── 7e) Revenue by Service ─────────────────────────────────────────────────
@router.get("/revenue-by-service")
def get_revenue_by_service(
    limit: int = 15,
    start_date: str = Query(None), end_date: str = Query(None),
    payment: str = Query(None),
) -> Dict[str, Any]:
    """Revenue grouped by clean service category. Joins payments to appointments via patient_id + date."""
    conn = _get_conn()
    try:
        if not _table_exists(conn, "payments_clean") or not _table_exists(conn, "appointments"):
            return {"data": []}
        if not _column_exists(conn, "appointments", "raw_text_service"):
            return {"data": []}
        date_col = "COALESCE(SUBSTR(p.appointment_date_raw, 1, 10), SUBSTR(p.loaded_at, 1, 10))"
        wh, params = ["p.patient_id IS NOT NULL", "p.net_received IS NOT NULL"], [limit]
        if _parse_date(start_date):
            wh.append(f"{date_col} >= ?")
            params.insert(-1, _parse_date(start_date))
        if _parse_date(end_date):
            wh.append(f"{date_col} <= ?")
            params.insert(-1, _parse_date(end_date))
        if payment:
            wh.append("LOWER(TRIM(p.payer_source_norm)) = LOWER(TRIM(?))")
            params.insert(-1, payment)
        join_sd = ""
        svc_expr = "COALESCE(sd.clean_service_category, 'سایر')"
        if _table_exists(conn, "service_dim"):
            join_sd = "LEFT JOIN service_dim sd ON sd.raw_service_text = TRIM(COALESCE(a.raw_text_service,''))"
        else:
            svc_expr = "COALESCE(a.raw_text_service, 'سایر')"
        sql = f"""
            SELECT {svc_expr} AS service, SUM(p.net_received) AS revenue, COUNT(*) AS txn_count
            FROM payments_clean p
            INNER JOIN appointments a ON a.patient_id = p.patient_id
                AND date(a.appointment_date) = date({date_col})
            {join_sd}
            WHERE {" AND ".join(wh)}
            GROUP BY service
            ORDER BY revenue DESC
            LIMIT ?
        """
        cur = conn.execute(sql, params)
        rows = cur.fetchall()
        return {"data": [{"service": r[0], "revenue": r[1], "txn_count": r[2]} for r in rows]}
    except sqlite3.OperationalError as e:
        logger.warning("revenue-by-service: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        conn.close()


# ─── 7f) Service Normalization Validation Report ────────────────────────────
@router.get("/service-normalization-report")
def get_service_normalization_report(limit: int = 100) -> Dict[str, Any]:
    """Top N raw service values (by appointment count) and their mapped clean_service_category for manual review."""
    conn = _get_conn()
    try:
        if not _table_exists(conn, "service_dim"):
            return {"data": [], "message": "service_dim not populated. Run scripts/populate_service_dim.py first."}
        if not _table_exists(conn, "appointments") or not _column_exists(conn, "appointments", "raw_text_service"):
            cur = conn.execute(
                """
                SELECT raw_service_text, clean_service_category, clean_service_subtype, is_noise, duration_hint_minutes
                FROM service_dim ORDER BY raw_service_text LIMIT ?
                """,
                (limit,),
            )
        else:
            cur = conn.execute(
                """
                SELECT sd.raw_service_text, sd.clean_service_category, sd.clean_service_subtype,
                       sd.is_noise, sd.duration_hint_minutes, COUNT(a.id) AS appt_count
                FROM service_dim sd
                LEFT JOIN appointments a ON TRIM(COALESCE(a.raw_text_service,'')) = sd.raw_service_text
                GROUP BY sd.raw_service_text
                ORDER BY appt_count DESC
                LIMIT ?
                """,
                (limit,),
            )
        rows = cur.fetchall()
        total = conn.execute("SELECT COUNT(*) FROM service_dim").fetchone()[0]
        if rows and len(rows[0]) >= 6:
            data = [
                {
                    "raw_service_text": r[0],
                    "clean_service_category": r[1],
                    "clean_service_subtype": r[2],
                    "is_noise": bool(r[3]),
                    "duration_hint_minutes": r[4],
                    "appointment_count": r[5],
                }
                for r in rows
            ]
        else:
            data = [
                {
                    "raw_service_text": r[0],
                    "clean_service_category": r[1],
                    "clean_service_subtype": r[2],
                    "is_noise": bool(r[3]),
                    "duration_hint_minutes": r[4],
                }
                for r in rows
            ]
        return {"data": data, "total_in_dim": total}
    except sqlite3.OperationalError as e:
        logger.warning("service-normalization-report: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        conn.close()


# ─── 8) Revenue Trend ──────────────────────────────────────────────────────
@router.get("/revenue-trend")
def get_revenue_trend(
    limit: int = 90,
    start_date: str = Query(None), end_date: str = Query(None),
    payment: str = Query(None),
) -> Dict[str, Any]:
    """Daily revenue. Filters: start_date, end_date, payment."""
    conn = _get_conn()
    try:
        if not _table_exists(conn, "payments_clean"):
            return {"data": []}
        date_col = "COALESCE(SUBSTR(appointment_date_raw, 1, 10), SUBSTR(loaded_at, 1, 10), date('now'))"
        wh, params = ["net_received IS NOT NULL"], [limit]
        if _parse_date(start_date):
            wh.append(f"{date_col} >= ?")
            params.insert(-1, _parse_date(start_date))
        if _parse_date(end_date):
            wh.append(f"{date_col} <= ?")
            params.insert(-1, _parse_date(end_date))
        if payment:
            wh.append("LOWER(TRIM(payer_source_norm)) = LOWER(TRIM(?))")
            params.insert(-1, payment)
        cur = conn.execute(
            f"""
            SELECT {date_col} AS day, SUM(net_received) AS total
            FROM payments_clean
            WHERE {" AND ".join(wh)}
            GROUP BY day
            ORDER BY day DESC
            LIMIT ?
            """,
            params,
        )
        rows = [{"day": r[0], "total": r[1]} for r in cur.fetchall()]
        rows.reverse()
        return {"data": rows}
    except sqlite3.OperationalError as e:
        logger.warning("revenue-trend: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        conn.close()
