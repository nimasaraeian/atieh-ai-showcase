# -*- coding: utf-8 -*-

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd

from app.engine.scoring import calculate_financial_score

DB = Path(r".\atieh_clinic.db")

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
    Load insurance priority catalog, if available.

    We intentionally mirror the search order used elsewhere in the app so that
    the same CSV that drives dashboards is also used for slot scoring.
    """
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
                return pd.read_csv(path, encoding="utf-8-sig")
            except Exception:
                # Any issue loading the CSV should not break scheduling;
                # we'll fall back to neutral financial scores.
                return pd.DataFrame()

    return pd.DataFrame()


def recommend_slots_from_db(payload: dict, top_n: int = 200) -> dict:
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
        financial_score = calculate_financial_score(
            insurance_name=insurance_name,
            insurance_priority_df=insurance_priority_df,
            default=0.5,
        )

        # Combine time- and insurance-value components into a single score.
        # We keep time slightly dominant so earlier clinic slots are still
        # preferred, but higher-value insurers get a meaningful boost.
        combined_score = 0.6 * time_score + 0.4 * financial_score

        recommendations.append(
            {
                "slot_id": row["slot_id"],
                "doctor_id": row["doctor_id"],
                "doctor_name": row["doctor_name"],
                "weekday": row["weekday_name"],
                "shift": row["shift_label"],
                "time": start_time,
                "floor": row["floor_label"],
                "unit": row["unit_label"],
                "score": round(combined_score, 3),
                "time_score": time_score,
                "financial_score": round(financial_score, 3),
            }
        )

    # Sort by combined score (descending) so that the highest-value
    # recommendations – considering both time and insurance value – appear first.
    recommendations.sort(key=lambda r: r.get("score", 0.0), reverse=True)

    return {
        "ok": True,
        "source": "doctor_time_slots",
        "count": len(recommendations),
        "preferred_day_input": preferred_day_en,
        "preferred_day_mapped": preferred_day_fa,
        "recommendations": recommendations,
    }