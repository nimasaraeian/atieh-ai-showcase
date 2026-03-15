# -*- coding: utf-8 -*-
"""
Patient priority profile: load raw data from patient_priority_profile_v1 view,
compute normalized scores (0–100), tier, and scheduling window.

Used by: reception API (expose profile), db_schedule_recommender (filter/rank slots).
"""
from __future__ import annotations

import json
import logging
import math
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from app.engine.patient_priority_config import (
    WEIGHTS,
    get_scheduling_window_days,
    get_tier_for_score,
    get_tier_label,
)

logger = logging.getLogger(__name__)

# Same DB as reception (master_patient_profile_v2, patient_insurance_profile_v2)
def _resolve_priority_db() -> Path:
    env_path = os.environ.get("FINANCIAL_DB_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)
    for name in ("atieh_clinic_recovery81_test.db", "atieh_clinic_working.db", "atieh_clinic.db"):
        p = Path(name)
        if p.exists():
            return p
    return Path("atieh_clinic_recovery81_test.db")


VIEW_NAME = "patient_priority_profile_v1"


def _clamp100(x: float) -> float:
    return max(0.0, min(100.0, float(x))) if x is not None else 0.0


def _log_norm(value: float, scale: float = 1.0, cap: float = 100.0) -> float:
    """Normalize positive value to 0–100 using log(1 + x/scale)."""
    if value is None or value <= 0:
        return 0.0
    try:
        v = math.log1p(value / scale) / math.log1p(100) * cap
        return _clamp100(v)
    except (TypeError, ValueError):
        return 0.0


def _insurance_score_from_lookup(
    insurance_name: Optional[str],
    conn: Optional[sqlite3.Connection],
) -> float:
    """Map insurance to 0–100 score. Cash=100; else lookup insurance_priority_rank or default 50."""
    if not insurance_name or not str(insurance_name).strip():
        return 50.0
    raw = str(insurance_name).strip()
    raw_upper = raw.upper()
    if raw_upper == "CASH":
        return 100.0
    try:
        from app.utils.fa_normalize import normalize_fa
        n = normalize_fa(raw)
        if n in ("نقد", "نقدی", "nakid", "cash"):
            return 100.0
    except Exception:
        pass
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT priority_score FROM insurance_priority_rank WHERE insurance_name = ? OR insurance_name LIKE ? LIMIT 1",
                (raw, f"%{raw}%"),
            )
            row = cur.fetchone()
            if row is not None and row[0] is not None:
                s = float(row[0])
                return _clamp100(s if s <= 100 else s)  # assume 0–100
        except sqlite3.OperationalError:
            pass
    return 50.0


def _recency_score_from_date(last_payment_date: Optional[str]) -> float:
    """0–100: more recent last payment = higher. No date = 0."""
    if not last_payment_date or not str(last_payment_date).strip():
        return 0.0
    s = str(last_payment_date).strip()
    try:
        # Try ISO or YYYY-MM-DD
        if "T" in s:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        else:
            parts = s.split(" ")[0].split("/")
            if len(parts) == 3:
                y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
                if y < 2000:  # Shamsi
                    dt = datetime(y + 621, m, d) if m <= 12 and d <= 31 else datetime.now()
                else:
                    dt = datetime(y, m, d)
            else:
                return 50.0
        days_ago = (datetime.now().replace(tzinfo=dt.tzinfo) - dt).days if dt.tzinfo else (datetime.now() - dt.replace(tzinfo=None)).days
        if days_ago <= 0:
            return 100.0
        if days_ago <= 30:
            return _clamp100(100 - days_ago * 2)
        if days_ago <= 90:
            return _clamp100(40 - (days_ago - 30) / 2)
        return max(0.0, 25 - (days_ago - 90) / 30)
    except Exception:
        return 50.0


def load_raw_profile(
    conn: sqlite3.Connection,
    record_no: Optional[str] = None,
    crm_patient_code: Optional[str] = None,
    patient_id: Optional[int] = None,
) -> Optional[dict[str, Any]]:
    """Load one row from patient_priority_profile_v1. Returns None if view missing or no row."""
    try:
        cur = conn.cursor()
        if record_no and str(record_no).strip():
            cur.execute(f"SELECT * FROM {VIEW_NAME} WHERE record_no = ? OR crm_patient_code = ? LIMIT 1", (str(record_no).strip(), str(record_no).strip()))
        elif crm_patient_code and str(crm_patient_code).strip():
            cur.execute(f"SELECT * FROM {VIEW_NAME} WHERE crm_patient_code = ? LIMIT 1", (str(crm_patient_code).strip(),))
        elif patient_id is not None:
            cur.execute(f"SELECT * FROM {VIEW_NAME} WHERE patient_id = ? LIMIT 1", (int(patient_id),))
        else:
            return None
        row = cur.fetchone()
        if not row:
            return None
        return dict(row)
    except sqlite3.OperationalError as e:
        logger.warning("patient_priority_profile_v1 not available: %s", e)
        return None


def compute_priority_profile(
    raw: dict[str, Any],
    insurance_conn: Optional[sqlite3.Connection] = None,
) -> dict[str, Any]:
    """
    Compute full priority profile from raw view row.
    Returns dict with patient_priority_score (0–100), patient_priority_tier, scheduling_window_days, etc.
    """
    visit_count = int(raw.get("visit_count") or 0)
    first_visit_year = raw.get("first_visit_year")
    last_year = raw.get("last_year")
    first_year = raw.get("first_visit_year") or raw.get("first_year")
    relationship_years = int(raw.get("relationship_years") or 0)
    lifetime_net_received = float(raw.get("lifetime_net_received") or 0)
    payment_count = int(raw.get("payment_count") or visit_count or 0)
    last_payment_date = raw.get("last_payment_date")
    insurance_name = raw.get("insurance_name")

    insurance_score = _insurance_score_from_lookup(insurance_name, insurance_conn)
    visit_score = _log_norm(visit_count, scale=5.0)  # 5 visits -> ~50, 20 -> ~80
    relationship_score = _clamp100(relationship_years * 5) if relationship_years else 0.0  # 20 years = 100
    financial_score = _log_norm(lifetime_net_received, scale=10_000_000)  # 10M Rial scale
    recency_score = _recency_score_from_date(last_payment_date)

    total = (
        WEIGHTS["insurance_score"] * insurance_score
        + WEIGHTS["visit_score"] * visit_score
        + WEIGHTS["relationship_score"] * relationship_score
        + WEIGHTS["financial_score"] * financial_score
        + WEIGHTS["recency_score"] * recency_score
    )
    patient_priority_score = round(_clamp100(total), 1)
    tier = get_tier_for_score(patient_priority_score)
    min_days, max_days = get_scheduling_window_days(tier)
    scheduling_window_days = max_days  # primary: max days ahead
    recommended_priority_band = tier

    explanation = {
        "insurance_score": round(insurance_score, 1),
        "visit_score": round(visit_score, 1),
        "relationship_score": round(relationship_score, 1),
        "financial_score": round(financial_score, 1),
        "recency_score": round(recency_score, 1),
        "weights": WEIGHTS,
        "tier": tier,
        "scheduling_window_min_days": min_days,
        "scheduling_window_max_days": max_days,
    }

    return {
        "patient_id": raw.get("patient_id"),
        "record_no": raw.get("record_no"),
        "crm_patient_code": raw.get("crm_patient_code"),
        "patient_name": raw.get("patient_name"),
        "insurance_name": insurance_name,
        "insurance_score": round(insurance_score, 1),
        "visit_count": visit_count,
        "visit_score": round(visit_score, 1),
        "first_visit_year": first_visit_year,
        "relationship_years": relationship_years,
        "relationship_score": round(relationship_score, 1),
        "total_payments": lifetime_net_received,
        "payment_count": payment_count,
        "lifetime_net_received": lifetime_net_received,
        "financial_score": round(financial_score, 1),
        "last_payment_date": last_payment_date,
        "recency_score": round(recency_score, 1),
        "patient_priority_score": patient_priority_score,
        "patient_priority_tier": tier,
        "patient_priority_tier_label": get_tier_label(tier),
        "scheduling_window_days": scheduling_window_days,
        "scheduling_window_min_days": min_days,
        "scheduling_window_max_days": max_days,
        "recommended_priority_band": recommended_priority_band,
        "explanation_json": json.dumps(explanation, ensure_ascii=False),
    }


def get_patient_priority_profile(
    record_no: Optional[str] = None,
    crm_patient_code: Optional[str] = None,
    patient_id: Optional[int] = None,
) -> Optional[dict[str, Any]]:
    """
    Load raw profile from DB and compute full priority profile.
    Returns None if DB/view missing or patient not found.
    """
    db = _resolve_priority_db()
    if not db.exists():
        logger.debug("Priority DB not found: %s", db)
        return None
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        raw = load_raw_profile(conn, record_no=record_no, crm_patient_code=crm_patient_code, patient_id=patient_id)
        if not raw:
            return None
        return compute_priority_profile(raw, insurance_conn=conn)
    finally:
        conn.close()
