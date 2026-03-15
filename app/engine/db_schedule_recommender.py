# -*- coding: utf-8 -*-

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd

from app.engine.scoring import calculate_financial_score
from app.utils.insurance_normalize import normalize_insurance_for_lookup

DB = Path(r".\atieh_clinic.db")

# CASH always has highest priority (payment_priority = 100 → financial_score = 1.0)
CASH_LABELS = {"cash", "نقد", "نقدی", "nakid", "cash"}

FA_SATURDAY = "\u0634\u0646\u0628\u0647"
FA_SUNDAY = "\u06cc\u06a9\u0634\u0646\u0628\u0647"
FA_MONDAY = "\u062f\u0648\u0634\u0646\u0628\u0647"
FA_TUESDAY = "\u0633\u0647 \u0634\u0646\u0628\u0647"
FA_TUESDAY_ZWNJ = "\u0633\u0647\u200c\u0634\u0646\u0628\u0647"
FA_WEDNESDAY = "\u0686\u0647\u0627\u0631\u0634\u0646\u0628\u0647"
FA_THURSDAY = "\u067e\u0646\u062c\u0634\u0646\u0628\u0647"
FA_FRIDAY = "\u062c\u0645\u0639\u0647"

SHIFT_CODE_MAP = {
    "morning": "D",
    "afternoon": "E",
    "night": "N",
}

# Persian weekday -> Python weekday (Monday=0, Sunday=6) for next-occurrence date calc
FA_WEEKDAY_TO_PY = {
    FA_MONDAY: 0,
    FA_TUESDAY: 1,
    FA_WEDNESDAY: 2,
    FA_THURSDAY: 3,
    FA_FRIDAY: 4,
    FA_SATURDAY: 5,
    FA_SUNDAY: 6,
    FA_TUESDAY_ZWNJ: 1,
}

# Persian weekday -> English for i18n
FA_WEEKDAY_TO_EN = {
    FA_SATURDAY: "Saturday",
    FA_SUNDAY: "Sunday",
    FA_MONDAY: "Monday",
    FA_TUESDAY: "Tuesday",
    FA_TUESDAY_ZWNJ: "Tuesday",
    FA_WEDNESDAY: "Wednesday",
    FA_THURSDAY: "Thursday",
    FA_FRIDAY: "Friday",
}


def _next_occurrence_date(weekday_py: int) -> str:
    """Return YYYY-MM-DD for the next occurrence of the given weekday (0=Mon, 6=Sun)."""
    today = datetime.now().date()
    today_weekday = today.weekday()
    days_ahead = (weekday_py - today_weekday + 7) % 7
    target = today + timedelta(days=days_ahead)
    return target.strftime("%Y-%m-%d")


def _normalize_day(day_value):
    if not day_value:
        return None

    s = str(day_value).strip().lower()

    day_map = {
        "monday": FA_MONDAY,
        "tuesday": FA_TUESDAY,
        "wednesday": FA_WEDNESDAY,
        "thursday": FA_THURSDAY,
        "friday": FA_FRIDAY,
        "saturday": FA_SATURDAY,
        "sunday": FA_SUNDAY,
        FA_MONDAY: FA_MONDAY,
        FA_TUESDAY: FA_TUESDAY,
        FA_TUESDAY_ZWNJ: FA_TUESDAY,
        FA_WEDNESDAY: FA_WEDNESDAY,
        FA_THURSDAY: FA_THURSDAY,
        FA_FRIDAY: FA_FRIDAY,
        FA_SATURDAY: FA_SATURDAY,
        FA_SUNDAY: FA_SUNDAY,
    }

    return day_map.get(s)


def _calc_time_score(slot_start: str) -> float:
    try:
        dt = datetime.strptime(slot_start, "%H:%M")
        minutes = dt.hour * 60 + dt.minute
        score = 1.0 - max(0, minutes - 480) / 720.0
        return round(max(0.0, min(1.0, score)), 3)
    except Exception:
        return 0.8


def _end_time_30m(slot_start: str) -> str:
    dt = datetime.strptime(slot_start, "%H:%M")
    return (dt + timedelta(minutes=30)).strftime("%H:%M")


def _load_insurance_priority_df() -> pd.DataFrame:
    """
    Load insurance priority catalog for slot scoring.

    Priority:
      1) SQLite insurance_priority_rank (from Excel تاریخ پرداختی بیمه ها.xlsx)
      2) CSV fallbacks

    Returns DataFrame with insurance_name, priority_score (0–1).
    CASH is always added with priority_score=1.0.
    """
    import os

    db_path = os.getenv("DATABASE_URL", "sqlite:///atieh_clinic.db")
    if db_path.startswith("sqlite:///"):
        db_path = db_path[len("sqlite:///"):]
    db = Path(db_path)

    if db.exists():
        try:
            conn = sqlite3.connect(str(db))
            cur = conn.cursor()
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='insurance_priority_rank'"
            )
            if cur.fetchone():
                rows = cur.execute(
                    "SELECT insurance_name, priority_score FROM insurance_priority_rank"
                ).fetchall()
                conn.close()
                # priority_score in DB is 0–100; convert to 0–1
                data = [
                    {"insurance_name": r[0], "priority_score": (r[1] or 25) / 100.0}
                    for r in rows
                ]
                data.append({"insurance_name": "CASH", "priority_score": 1.0})
                return pd.DataFrame(data)
            conn.close()
        except Exception:
            pass

    candidate_paths = [
        "data/outputs/insurance_priority.csv",
        "data/inputs/payments/insurance_payment_priority.csv",
        "data/inputs/payments/insurance_priority.csv",
        "data/reference/insurance_payment_priority.csv",
        "data/inputs/reference/insurance_payment_priority.csv",
    ]
    for p in candidate_paths:
        path = Path(p)
        if path.exists():
            try:
                df = pd.read_csv(path, encoding="utf-8-sig")
                # Normalize scores to 0–1 if stored as 0–100
                if "priority_score" in df.columns and df["priority_score"].max() > 1.5:
                    df = df.copy()
                    df["priority_score"] = df["priority_score"] / 100.0
                return df
            except Exception:
                pass

    return pd.DataFrame()


def _is_cash(insurance_name: str) -> bool:
    if not insurance_name:
        return False
    s = str(insurance_name).strip().upper()
    if s == "CASH":
        return True
    try:
        from app.utils.fa_normalize import normalize_fa
        n = normalize_fa(insurance_name)
        return n in ("نقد", "نقدی", "nakid", "cash")
    except Exception:
        return False


def _get_financial_score(
    insurance_name: str | None,
    insurance_priority_df: pd.DataFrame,
    default: float = 0.5,
) -> float:
    """
    Payment priority for slot scoring.
    CASH → 1.0; else lookup in insurance_priority_rank using normalized name.
    """
    if not insurance_name or not str(insurance_name).strip():
        return default
    raw = str(insurance_name).strip()
    if _is_cash(raw):
        return 1.0
    lookup = normalize_insurance_for_lookup(raw) or raw
    return calculate_financial_score(
        lookup,
        insurance_priority_df,
        default,
    )


def recommend_slots_from_db(payload: dict, top_n: int = 200) -> dict:
    """DEPRECATED: Overridden by patient-aware version below. Kept for reference only."""
    if not DB.exists():
        return {
            "ok": False,
            "source": "doctor_time_slots",
            "recommendations": [],
            "message": f"Database not found: {DB}",
        }

    preferred_day_en = payload.get("preferred_day")
    preferred_day_fa = _normalize_day(preferred_day_en)

    insurance_name = payload.get("insurance") or None

    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    sql = """
    SELECT
        t.slot_id,
        d.doctor_id,
        d.doctor_name,
        t.weekday_name,
        t.shift_label,
        t.slot_start,
        COALESCE(t.floor_label, d.floor_label, '') AS floor_label,
        COALESCE(t.unit_label, '') AS unit_label
    FROM doctor_time_slots t
    JOIN doctor_master d
      ON d.doctor_id = t.doctor_id
    WHERE t.availability_status = 'available'
    """
    params = []

    if preferred_day_fa:
        sql += " AND t.weekday_name = ? "
        params.append(preferred_day_fa)

    sql += """
    ORDER BY
        t.weekday_name,
        t.slot_start,
        d.doctor_name
    LIMIT ?
    """
    params.append(top_n)

    rows = cur.execute(sql, params).fetchall()
    conn.close()

    # Load insurance priority table once per request so we can factor insurer
    # value into the final score for each slot.
    insurance_priority_df = _load_insurance_priority_df()

    recommendations = []

    for row in rows:
        start_time = row["slot_start"]

        try:
            hh, mm = map(int, start_time.split(":"))
        except Exception:
            continue

        if hh < 8 or hh > 20:
            continue

        time_score = _calc_time_score(start_time)
        financial_score = _get_financial_score(
            insurance_name,
            insurance_priority_df,
            0.5,
        )

        # Combine time- and insurance-value components into a single score.
        combined_score = 0.6 * time_score + 0.4 * financial_score

        weekday_fa = str(row["weekday_name"] or "").strip()
        weekday_py = FA_WEEKDAY_TO_PY.get(weekday_fa)
        slot_date = _next_occurrence_date(weekday_py) if weekday_py is not None else None
        weekday_en = FA_WEEKDAY_TO_EN.get(weekday_fa) if weekday_fa else None

        rec = {
            "slot_id": row["slot_id"],
            "doctor_id": row["doctor_id"],
            "doctor_name": row["doctor_name"],
            "weekday": weekday_fa or row["weekday_name"],
            "weekday_en": weekday_en,
            "date": slot_date,
            "shift": row["shift_label"],
            "time": start_time,
            "floor": row["floor_label"],
            "unit": row["unit_label"],
            "score": round(combined_score, 3),
            "time_score": time_score,
            "financial_score": round(financial_score, 3),
        }
        recommendations.append(rec)

    # Sort by combined score (descending) so that the highest-value
    # recommendations â€“ considering both time and insurance value â€“ appear first.
    recommendations.sort(key=lambda r: r.get("score", 0.0), reverse=True)

    return {
        "ok": True,
        "source": "doctor_time_slots",
        "count": len(recommendations),
        "preferred_day_input": preferred_day_en,
        "preferred_day_mapped": preferred_day_fa,
        "recommendations": recommendations,
    }
# =========================
# PATIENT-AWARE PATCH OVERRIDE
# =========================

from pathlib import Path as _Path

try:
    from app.engine.patient_priority import get_patient_priority_profile
except ImportError:
    get_patient_priority_profile = None


def _resolve_slots_db() -> _Path:
    p = _Path(r".\atieh_clinic.db")
    return p

def _resolve_financial_db() -> _Path:
    for p in (_Path(r".\atieh_clinic_working.db"), _Path(r".\atieh_clinic.db")):
        if p.exists():
            return p
    return _Path(r".\atieh_clinic_working.db")
import sqlite3 as _sqlite3

def _resolve_recommend_db() -> _Path:
    for p in (_Path(r".\atieh_clinic_working.db"), _Path(r".\atieh_clinic.db")):
        if p.exists():
            return p
    return _Path(r".\atieh_clinic.db")

def _clamp01(x):
    try:
        x = float(x)
    except Exception:
        return 0.0
    if x < 0:
        return 0.0
    if x > 1:
        return 1.0
    return x

def _coerce_score01(v, default=0.0):
    if v is None:
        return default
    try:
        x = float(v)
    except Exception:
        return default
    if x > 1.0:
        x = x / 100.0
    return _clamp01(x)

def _tier_boost(tier: str) -> float:
    t = (tier or "").strip().upper()
    if t == "VIP":
        return 0.08
    if t == "HIGH":
        return 0.05
    if t == "MEDIUM":
        return 0.02
    return 0.0

def _load_patient_context(record_no: str) -> dict:
    ctx = {
        "record_no_used": record_no,
        "financial_tier": None,
        "financial_value_score": None,
        "lifetime_net_received": None,
        "last_payment_date_raw": None,
        "in_followup_queue": False,
        "in_scheduling_top300": False,
        "scheduling_band": None,
        "scheduling_priority_score": None,
        "patient_priority_score": 0.0,
        "patient_value_score": 0.0,
        "followup_boost": 0.0,
        "top300_boost": 0.0,
        "tier_boost": 0.0,
    }

    rn = str(record_no or "").strip()
    if not rn:
        return ctx

    slots_db = _resolve_slots_db()
    if not slots_db.exists():
        return ctx

    conn = _sqlite3.connect(str(slots_db))
    conn.row_factory = _sqlite3.Row
    cur = conn.cursor()

    try:
        try:
            row = cur.execute(
                """
                SELECT
                    record_no,
                    financial_tier,
                    financial_value_score,
                    lifetime_net_received,
                    last_payment_date_raw
                FROM financial_identity_profile
                WHERE record_no = ?
                LIMIT 1
                """,
                (rn,),
            ).fetchone()
            if row:
                d = dict(row)
                ctx["financial_tier"] = d.get("financial_tier")
                ctx["financial_value_score"] = d.get("financial_value_score")
                ctx["lifetime_net_received"] = d.get("lifetime_net_received")
                ctx["last_payment_date_raw"] = d.get("last_payment_date_raw")
        except _sqlite3.OperationalError:
            pass

        try:
            row = cur.execute(
                """
                SELECT action_type
                FROM v_financial_followup_queue_contactable
                WHERE record_no = ?
                LIMIT 1
                """,
                (rn,),
            ).fetchone()
            if row:
                ctx["in_followup_queue"] = True
        except _sqlite3.OperationalError:
            pass

        try:
            row = cur.execute(
                """
                SELECT scheduling_band, scheduling_priority_score
                FROM v_financial_scheduling_queue_top300
                WHERE record_no = ?
                LIMIT 1
                """,
                (rn,),
            ).fetchone()
            if row:
                ctx["in_scheduling_top300"] = True
                ctx["scheduling_band"] = row[0]
                ctx["scheduling_priority_score"] = row[1]
        except _sqlite3.OperationalError:
            pass

    finally:
        conn.close()

    ctx["patient_value_score"] = _coerce_score01(ctx["financial_value_score"], default=0.0)
    ctx["patient_priority_score"] = _coerce_score01(ctx["scheduling_priority_score"], default=0.0)
    ctx["followup_boost"] = 0.08 if ctx["in_followup_queue"] else 0.0
    ctx["top300_boost"] = 0.12 if ctx["in_scheduling_top300"] else 0.0
    ctx["tier_boost"] = _tier_boost(ctx["financial_tier"])

    return ctx


TOP_N_RECOMMENDATIONS = 3


def recommend_slots_from_db(payload: dict, top_n: int = 50) -> dict:
    """Single active implementation. Uses real doctor_time_slots, patient context. Output capped at top 3."""
    slots_db = _resolve_slots_db()

    if not slots_db.exists():
        return {
            "ok": False,
            "source": "doctor_time_slots",
            "recommendations": [],
            "message": f"Slots database not found: {slots_db}",
        }

    preferred_day_en = payload.get("preferred_day") or payload.get("weekday")
    preferred_day_fa = _normalize_day(preferred_day_en)

    insurance_name = payload.get("insurance") or None
    record_no = str(payload.get("record_no") or "").strip() or None
    crm_code = str(payload.get("crm_patient_code") or "").strip() or None
    doctor_id = payload.get("doctor") or payload.get("doctor_id")
    if doctor_id is not None:
        try:
            doctor_id = int(doctor_id)
        except (TypeError, ValueError):
            doctor_id = None

    patient_ctx = _load_patient_context(record_no)
    priority_profile = None
    if get_patient_priority_profile and (record_no or crm_code):
        try:
            priority_profile = get_patient_priority_profile(record_no=record_no, crm_patient_code=crm_code)
            if priority_profile:
                patient_ctx["priority_profile"] = priority_profile
                patient_ctx["patient_priority_score"] = (priority_profile.get("patient_priority_score") or 0) / 100.0
                patient_ctx["patient_priority_tier"] = priority_profile.get("patient_priority_tier")
                patient_ctx["scheduling_window_min_days"] = priority_profile.get("scheduling_window_min_days", 0)
                patient_ctx["scheduling_window_max_days"] = priority_profile.get("scheduling_window_max_days", 14)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Failed to load patient priority profile: %s", e)

    conn = sqlite3.connect(str(slots_db))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    sql = """
    SELECT
        t.slot_id,
        d.doctor_id,
        d.doctor_name,
        t.weekday_name,
        t.shift_label,
        t.slot_start,
        COALESCE(t.floor_label, d.floor_label, '') AS floor_label,
        COALESCE(t.unit_label, '') AS unit_label
    FROM doctor_time_slots t
    JOIN doctor_master d
      ON d.doctor_id = t.doctor_id
    WHERE t.availability_status = 'available'
    """
    params = []

    if preferred_day_fa:
        sql += " AND t.weekday_name = ? "
        params.append(preferred_day_fa)
    if doctor_id is not None:
        sql += " AND d.doctor_id = ? "
        params.append(doctor_id)

    sql += """
    ORDER BY
        t.weekday_name,
        t.slot_start,
        d.doctor_name
    LIMIT ?
    """
    params.append(top_n)

    rows = cur.execute(sql, params).fetchall()
    conn.close()

    if priority_profile and rows:
        min_days = patient_ctx.get("scheduling_window_min_days", 0)
        max_days = patient_ctx.get("scheduling_window_max_days", 365)
        today = datetime.now().date()
        filtered = []
        for row in rows:
            weekday_fa = str(row["weekday_name"] or "").strip()
            weekday_py = FA_WEEKDAY_TO_PY.get(weekday_fa)
            if weekday_py is not None:
                slot_date_str = _next_occurrence_date(weekday_py)
                slot_d = datetime.strptime(slot_date_str, "%Y-%m-%d").date()
                days_ahead = (slot_d - today).days
                if min_days <= days_ahead <= max_days:
                    filtered.append(row)
            else:
                filtered.append(row)
        if filtered:
            rows = filtered

    insurance_priority_df = _load_insurance_priority_df()

    recommendations = []

    for row in rows:
        start_time = row["slot_start"]

        try:
            hh, mm = map(int, start_time.split(":"))
        except Exception:
            continue

        if hh < 8 or hh > 20:
            continue

        time_score = _calc_time_score(start_time)
        financial_score = _get_financial_score(
            insurance_name,
            insurance_priority_df,
            0.5,
        )

        patient_priority_score = patient_ctx["patient_priority_score"]
        patient_value_score = patient_ctx["patient_value_score"]
        followup_boost = patient_ctx["followup_boost"]
        top300_boost = patient_ctx["top300_boost"]
        tier_boost = patient_ctx["tier_boost"]

        final_score = (
    0.55 * time_score +
    0.15 * financial_score +
    0.12 * patient_priority_score +
    0.08 * patient_value_score +
    0.04 * (1.0 if patient_ctx["in_followup_queue"] else 0.0) +
    0.04 * (1.0 if patient_ctx["in_scheduling_top300"] else 0.0) +
    0.02 * (1.0 if patient_ctx["financial_tier"] == "VIP" else 0.5 if patient_ctx["financial_tier"] == "HIGH" else 0.2 if patient_ctx["financial_tier"] == "MEDIUM" else 0.0)
)
        final_score = round(_clamp01(final_score), 3)

        reasons = []
        if patient_ctx.get("patient_priority_tier"):
            reasons.append(f"PATIENT_TIER_{patient_ctx['patient_priority_tier']}")
        if patient_ctx.get("scheduling_window_max_days") is not None:
            reasons.append(f"SCHEDULING_WINDOW_DAYS_{patient_ctx.get('scheduling_window_max_days')}")
        if doctor_id is not None:
            reasons.append("PREFERRED_DOCTOR_FILTER")
        if patient_ctx["financial_tier"]:
            reasons.append(f"TIER_{patient_ctx['financial_tier']}")
        if patient_ctx["in_followup_queue"]:
            reasons.append("FOLLOWUP_BOOST")
        if patient_ctx["in_scheduling_top300"]:
            reasons.append("TOP300_BOOST")
        if patient_ctx["scheduling_band"]:
            reasons.append(f"BAND_{patient_ctx['scheduling_band']}")
        if time_score >= 0.85:
            reasons.append("EARLY_SLOT")
        if financial_score >= 0.7:
            reasons.append("INSURANCE_PRIORITY")

        weekday_fa = str(row["weekday_name"] or "").strip()
        weekday_py = FA_WEEKDAY_TO_PY.get(weekday_fa)
        slot_date = _next_occurrence_date(weekday_py) if weekday_py is not None else None
        weekday_en = FA_WEEKDAY_TO_EN.get(weekday_fa) if weekday_fa else None

        # When no doctor filter: do not suggest a doctor (clinic-level slot)
        rec_doctor_id = row["doctor_id"] if doctor_id is not None else None
        rec_doctor_name = row["doctor_name"] if doctor_id is not None else None
        rec = {
            "slot_id": row["slot_id"],
            "doctor_id": rec_doctor_id,
            "doctor_name": rec_doctor_name,
            "weekday": weekday_fa or row["weekday_name"],
            "weekday_en": weekday_en,
            "date": slot_date,
            "shift": row["shift_label"],
            "time": start_time,
            "floor": row["floor_label"],
            "unit": row["unit_label"],
            "score": final_score,
            "final_score": final_score,
            "time_score": round(time_score, 3),
            "financial_score": round(financial_score, 3),
            "patient_priority_score": round(patient_priority_score, 3),
            "patient_value_score": round(patient_value_score, 3),
            "followup_boost": round(followup_boost, 3),
            "top300_boost": round(top300_boost, 3),
            "tier_boost": round(tier_boost, 3),
            "reasons": reasons,
        }
        if patient_ctx.get("patient_priority_tier"):
            rec["patient_priority_tier"] = patient_ctx["patient_priority_tier"]
            rec["scheduling_window_days"] = patient_ctx.get("scheduling_window_max_days")
        rec["preferred_doctor_filter"] = doctor_id is not None
        recommendations.append(rec)

    recommendations = sorted(
        recommendations,
        key=lambda x: x.get("final_score", x.get("score", 0)),
        reverse=True,
    )
    recommendations = recommendations[:TOP_N_RECOMMENDATIONS]
    count = len(recommendations)

    out = {
        "ok": True,
        "source": "doctor_time_slots",
        "count": count,
        "preferred_day_input": preferred_day_en,
        "preferred_day_mapped": preferred_day_fa,
        "record_no_used": record_no,
        "preferred_doctor_filter": doctor_id is not None,
        "patient_context": {
            "financial_tier": patient_ctx["financial_tier"],
            "financial_value_score": patient_ctx["financial_value_score"],
            "lifetime_net_received": patient_ctx["lifetime_net_received"],
            "last_payment_date_raw": patient_ctx["last_payment_date_raw"],
            "in_followup_queue": patient_ctx["in_followup_queue"],
            "in_scheduling_top300": patient_ctx["in_scheduling_top300"],
            "scheduling_band": patient_ctx["scheduling_band"],
            "scheduling_priority_score": patient_ctx["scheduling_priority_score"],
            "patient_priority_score": round(patient_ctx["patient_priority_score"], 3),
            "patient_value_score": round(patient_ctx["patient_value_score"], 3),
            "followup_boost": round(patient_ctx["followup_boost"], 3),
            "top300_boost": round(patient_ctx["top300_boost"], 3),
            "tier_boost": round(patient_ctx["tier_boost"], 3),
        },
        "score_formula": "0.45*time + 0.15*insurance + 0.20*patient_priority + 0.10*patient_value + followup_boost + top300_boost + tier_boost",
        "recommendations": recommendations,
    }
    if priority_profile:
        out["patient_priority_profile"] = priority_profile
        out["patient_context"]["patient_priority_tier"] = priority_profile.get("patient_priority_tier")
        out["patient_context"]["scheduling_window_days"] = priority_profile.get("scheduling_window_max_days")
    return out




# =========================
# FORCE FIX: patient context loader override
# =========================

def _load_patient_context(record_no: str) -> dict:
    ctx = {
        "record_no_used": record_no,
        "financial_tier": None,
        "financial_value_score": None,
        "lifetime_net_received": None,
        "last_payment_date_raw": None,
        "in_followup_queue": False,
        "in_scheduling_top300": False,
        "scheduling_band": None,
        "scheduling_priority_score": None,
        "patient_priority_score": 0.0,
        "patient_value_score": 0.0,
        "followup_boost": 0.0,
        "top300_boost": 0.0,
        "tier_boost": 0.0,
    }

    rn = str(record_no or "").strip()
    if not rn:
        return ctx

    fin_db = _resolve_financial_db()
    if not fin_db.exists():
        return ctx

    conn = _sqlite3.connect(str(fin_db))
    conn.row_factory = _sqlite3.Row
    cur = conn.cursor()

    try:
        row = None
        try:
            row = cur.execute(
                """
                SELECT
                    record_no,
                    financial_tier,
                    financial_value_score,
                    lifetime_net_received,
                    last_payment_date_raw
                FROM financial_identity_profile
                WHERE CAST(record_no AS TEXT) = ?
                LIMIT 1
                """,
                (rn,),
            ).fetchone()
        except _sqlite3.OperationalError:
            row = None

        if row:
            d = dict(row)
            ctx["financial_tier"] = d.get("financial_tier")
            ctx["financial_value_score"] = d.get("financial_value_score")
            ctx["lifetime_net_received"] = d.get("lifetime_net_received")
            ctx["last_payment_date_raw"] = d.get("last_payment_date_raw")

        try:
            f_row = cur.execute(
                """
                SELECT action_type
                FROM v_financial_followup_queue_contactable
                WHERE CAST(record_no AS TEXT) = ?
                LIMIT 1
                """,
                (rn,),
            ).fetchone()
            if f_row:
                ctx["in_followup_queue"] = True
        except _sqlite3.OperationalError:
            pass

        try:
            s_row = cur.execute(
                """
                SELECT scheduling_band, scheduling_priority_score
                FROM v_financial_scheduling_queue_top300
                WHERE CAST(record_no AS TEXT) = ?
                LIMIT 1
                """,
                (rn,),
            ).fetchone()
            if s_row:
                ctx["in_scheduling_top300"] = True
                ctx["scheduling_band"] = s_row[0]
                ctx["scheduling_priority_score"] = s_row[1]
        except _sqlite3.OperationalError:
            pass

    finally:
        conn.close()

    ctx["patient_value_score"] = _coerce_score01(ctx["financial_value_score"], default=0.0)
    ctx["patient_priority_score"] = _coerce_score01(ctx["scheduling_priority_score"], default=0.0)
    ctx["followup_boost"] = 0.08 if ctx["in_followup_queue"] else 0.0
    ctx["top300_boost"] = 0.12 if ctx["in_scheduling_top300"] else 0.0
    ctx["tier_boost"] = _tier_boost(ctx["financial_tier"])

    return ctx
