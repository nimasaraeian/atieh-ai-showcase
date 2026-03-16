# -*- coding: utf-8 -*-

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pandas as pd

from app.engine.scoring import calculate_financial_score
from app.utils.insurance_normalize import normalize_insurance_for_lookup

import os

# Global, legacy-only default (kept for backward compatibility where DB is used
# directly from this module). New code should go via _resolve_slots_db /
# _resolve_financial_db which honour environment overrides and test DB.
_db_path = os.getenv("ATIEH_DB_PATH", "atieh_clinic_recovery81_test.db")
DB = Path(_db_path)

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


def _clinic_now() -> datetime:
    """
    Return current datetime in clinic local timezone (Asia/Tehran by default).
    Falls back to naive local time if timezone data is not available.
    """
    try:
        # Python 3.9+: use zoneinfo if available
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Tehran"))
    except Exception:
        # Fallback: use local time (assumed server already configured to clinic TZ)
        return datetime.now()


def _next_occurrence_date(weekday_py: int) -> str:
    """Return YYYY-MM-DD for the next occurrence of the given weekday (0=Mon, 6=Sun) using clinic today."""
    today = _clinic_now().date()
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


def _resolve_base_db() -> _Path:
    """
    Single source of truth for the main SQLite DB used by the scheduling
    recommender.

    Resolution order:
      1) ATIEH_DB_PATH environment variable (highest priority)
      2) atieh_clinic_recovery81_test.db (validated/test DB)
      3) atieh_clinic_working.db
      4) atieh_clinic.db (legacy fallback)
    """
    env_path = os.getenv("ATIEH_DB_PATH")
    if env_path:
        p = _Path(env_path)
        if p.exists():
            return p
    for name in (
        "atieh_clinic_recovery81_test.db",
        "atieh_clinic_working.db",
        "atieh_clinic.db",
    ):
        p = _Path(name)
        if p.exists():
            return p
    # Final fallback (may not exist, but keeps a deterministic path)
    return _Path("atieh_clinic_recovery81_test.db")


def _resolve_slots_db() -> _Path:
    # Slots live in the same DB as validation/test unless explicitly overridden.
    return _resolve_base_db()


def _resolve_financial_db() -> _Path:
    """
    Financial truth source resolution.

    Uses FINANCIAL_DB_PATH when set, otherwise follows the same order as
    _resolve_base_db so that financial views like patient_value_score_v2_final
    are read from the same file as validation/analysis.
    """
    env_path = os.getenv("FINANCIAL_DB_PATH")
    if env_path:
        p = _Path(env_path)
        if p.exists():
            return p
    return _resolve_base_db()


import sqlite3 as _sqlite3


def _resolve_recommend_db() -> _Path:
    # Kept for compatibility where an explicit "recommend DB" is needed – now
    # just an alias of the slots DB resolution.
    return _resolve_base_db()

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


def _window_preference_score(days_ahead: int, patient_ctx: dict) -> float:
    """
    Preferred-window score (0–1) based on the same preferred/allowed window model
    exposed to the UI via patient_priority_profile.

    - Inside preferred window => high score.
    - Outside preferred but inside allowed => low score (unless preferred is empty/unavailable).
    """
    try:
        d = int(days_ahead)
    except Exception:
        return 0.5

    allowed_min = int(patient_ctx.get("scheduling_window_min_days", 0) or 0)
    allowed_max = int(patient_ctx.get("scheduling_window_max_days", 21) or 21)
    pref_min = patient_ctx.get("scheduling_preferred_min_days")
    pref_max = patient_ctx.get("scheduling_preferred_max_days")

    try:
        pref_min = int(pref_min) if pref_min is not None else None
        pref_max = int(pref_max) if pref_max is not None else None
    except Exception:
        pref_min, pref_max = None, None

    # If preferred window is not available, fallback to a mild "earlier is slightly better".
    if pref_min is None or pref_max is None or pref_max < pref_min:
        if allowed_max <= allowed_min:
            return 0.5
        pos = (d - allowed_min) / float(max(1, allowed_max - allowed_min))
        pos = max(0.0, min(1.0, pos))
        return 0.6 - 0.2 * pos  # 0.6 early .. 0.4 late

    # Clamp preferred inside allowed (safety)
    pref_min = max(allowed_min, pref_min)
    pref_max = min(allowed_max, pref_max)

    tier = str(patient_ctx.get("patient_priority_tier") or "").upper()

    # Dedicated behaviour for P5 (normal patients):
    # - 0..4 days  : allowed but clearly penalized vs preferred
    # - 5..12 days : highest scoring band
    # - 13..14 days: acceptable but below preferred
    if tier == "P5":
        if pref_min <= d <= pref_max:
            return 1.0
        if d < pref_min:
            # Near-term early slots: allowed but strongly down-ranked relative to preferred.
            return 0.05
        if d > pref_max and d <= allowed_max:
            # Slightly beyond preferred but still in allowed window.
            return 0.25
        # Outside allowed window (should normally be filtered); keep very low.
        return 0.0

    # Default behaviour for other tiers:
    if pref_min <= d <= pref_max:
        # Inside preferred window: emphasize.
        return 0.95
    # Outside preferred but still allowed: strongly down-rank when preferred exists.
    return 0.15

def _load_patient_context(record_no: str) -> dict:
    """
    Load patient-level financial + scheduling context for a given record_no.

    Financial truth source precedence:
      1) patient_value_score_v2_final (final, aggregated financial layer; patient_id-level)
      2) financial_identity_profile (legacy view – record_no-level fallback only)

    Scheduling / follow-up truth source:
      - v_financial_followup_queue_contactable
      - v_financial_scheduling_queue_top300

    All numeric scores are normalised to 0–1 in this context; the underlying
    tables/views may store them as 0–100 or raw amounts.
    """
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
        # 1) Final financial layer (patient_id-level):
        #    - patient_value_score_v2_final does NOT have record_no
        #    - resolve patient_id from record_no using master_patient_profile_v2
        patient_id = None
        try:
            pid_row = cur.execute(
                """
                SELECT patient_id
                FROM master_patient_profile_v2
                WHERE CAST(crm_patient_code AS TEXT) = CAST(? AS TEXT)
                LIMIT 1
                """,
                (rn,),
            ).fetchone()
            # Fallback: some schemas may store record_no separately
            if not pid_row:
                try:
                    pid_row = cur.execute(
                        """
                        SELECT patient_id
                        FROM master_patient_profile_v2
                        WHERE CAST(record_no AS TEXT) = CAST(? AS TEXT)
                        LIMIT 1
                        """,
                        (rn,),
                    ).fetchone()
                except _sqlite3.OperationalError:
                    pid_row = None
            if pid_row and pid_row[0] is not None:
                try:
                    patient_id = int(pid_row[0])
                except Exception:
                    patient_id = None
        except _sqlite3.OperationalError:
            patient_id = None

        fin_row = None
        if patient_id is not None:
            try:
                fin_row = cur.execute(
                    """
                    SELECT
                        patient_id,
                        patient_value_score,
                        financial_tier,
                        lifetime_net_received_toman,
                        last_jalali_year
                    FROM patient_value_score_v2_final
                    WHERE patient_id = ?
                    LIMIT 1
                    """,
                    (patient_id,),
                ).fetchone()
            except _sqlite3.OperationalError:
                fin_row = None

        if fin_row:
            d = dict(fin_row)
            ctx["financial_tier"] = d.get("financial_tier")
            ctx["financial_value_score"] = d.get("patient_value_score")
            # Stored as lifetime_net_received_toman in v2_final
            ctx["lifetime_net_received"] = d.get("lifetime_net_received_toman")
            # last_payment_date_raw is not in v2_final; keep null unless we can
            # safely populate from legacy identity view below.
            ctx["last_payment_date_raw"] = None

        # 2) Fallback (legacy record_no-level) for missing fields only
        #    - do NOT override v2_final tier/value when present
        try:
            legacy = cur.execute(
                """
                SELECT
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
            legacy = None

        if legacy:
            ld = dict(legacy)
            if ctx["financial_tier"] is None:
                ctx["financial_tier"] = ld.get("financial_tier")
            if ctx["financial_value_score"] is None:
                ctx["financial_value_score"] = ld.get("financial_value_score")
            if ctx["lifetime_net_received"] is None:
                ctx["lifetime_net_received"] = ld.get("lifetime_net_received")
            # Only fill last_payment_date_raw from legacy if we don't have it.
            if ctx["last_payment_date_raw"] is None:
                ctx["last_payment_date_raw"] = ld.get("last_payment_date_raw")

        # Follow-up queue membership
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

        # Scheduling queue (TOP300) membership
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

    ctx["patient_value_score"] = _coerce_score01(
        ctx["financial_value_score"],
        default=0.0,
    )
    ctx["patient_priority_score"] = _coerce_score01(
        ctx["scheduling_priority_score"],
        default=0.0,
    )
    ctx["followup_boost"] = 0.08 if ctx["in_followup_queue"] else 0.0
    ctx["top300_boost"] = 0.12 if ctx["in_scheduling_top300"] else 0.0
    ctx["tier_boost"] = _tier_boost(ctx["financial_tier"])

    return ctx


TOP_N_RECOMMENDATIONS = 5


def _parse_ymd(date_str: str):
    try:
        s = str(date_str or "").strip()
        if not s:
            return None
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def _generate_dates_for_weekday_within_window(
    weekday_py: int,
    min_days: int,
    max_days: int,
):
    """
    Generate all concrete calendar dates for a given Python weekday (0=Monday)
    within [min_days, max_days] days ahead from clinic 'today'.
    """
    today = _clinic_now().date()
    dates = []
    if max_days < min_days:
        return dates
    for delta in range(int(min_days), int(max_days) + 1):
        d = today + timedelta(days=delta)
        if d.weekday() == int(weekday_py):
            dates.append((d, delta))
    return dates


def _diversify_by_date(sorted_recs: list[dict], k: int = 5) -> list[dict]:
    """
    Enforce date-level diversity over already-sorted recommendations.

    Strategy (two-pass, as requested):
      1) Group candidates by concrete slot date (`rec['date']`).
      2) PASS 1 (date diversity):
         - Take the best slot (highest score) from each date group.
         - Order those by score and keep up to k.
      3) PASS 2 (fill remaining):
         - If still need more, take the 2nd-best per date, then 3rd-best, etc.,
           each wave ordered by score, until k is reached.

    Notes:
      - Does not fabricate dates; only re-orders/filters real candidates.
      - If unique dates < k, some dates will contribute 2+ slots, but only
        after every date has had a chance to appear.
    """
    if not sorted_recs or k <= 0:
        return []

    # Group by date key
    buckets: dict[str, list[dict]] = {}
    for rec in sorted_recs:
        date_key = str(rec.get("date") or "")  # empty string for unknown
        buckets.setdefault(date_key, []).append(rec)

    # Ensure each bucket is sorted by score descending (in case caller didn't)
    def _score(x: dict) -> float:
        try:
            return float(x.get("final_score", x.get("score", 0.0)) or 0.0)
        except Exception:
            return 0.0

    for dk, items in buckets.items():
        buckets[dk] = sorted(items, key=_score, reverse=True)

    selected: list[dict] = []
    used_ids: set[int] = set()

    def _id_for(rec: dict) -> int:
        return id(rec)

    # Helper to add a wave of index-th items across all dates, ordered by score
    def _add_wave(idx: int):
        nonlocal selected
        wave: list[dict] = []
        for dk, items in buckets.items():
            if idx < len(items):
                cand = items[idx]
                sid = _id_for(cand)
                if sid not in used_ids:
                    wave.append(cand)
        # Order this wave by score
        wave.sort(key=_score, reverse=True)
        for cand in wave:
            sid = _id_for(cand)
            if sid in used_ids:
                continue
            selected.append(cand)
            used_ids.add(sid)
            if len(selected) >= k:
                return True
        return False

    # PASS 1: best per date (index 0)
    if _add_wave(0):
        return selected[:k]

    # PASS 2+: 2nd-best, 3rd-best, ... per date as needed
    max_bucket_len = max(len(v) for v in buckets.values())
    for idx in range(1, max_bucket_len):
        if _add_wave(idx):
            break

    return selected[:k]

def _group_recommendations_by_datetime(
    sorted_recs: list[dict],
    *,
    key_fields: tuple[str, ...] = ("date", "time", "weekday_en"),
) -> list[dict]:
    """
    Group repeated recommendations that are effectively the same visible time-slot.

    This prevents showing clones like:
      Friday 09:00 Unit 6
      Friday 09:00 Unit 10
      Friday 09:00 Unit 2

    Instead we return ONE recommendation with:
      - capacity_count: number of underlying units/slots
      - slot_ids: list of slot_id candidates
      - unit_options: list of {slot_id, unit, floor}

    Important:
    - No artificial diversity is created; we only *aggregate* real candidates.
    - Representative score is max(final_score) among the grouped items.
    """
    if not sorted_recs:
        return []

    buckets: dict[tuple, list[dict]] = {}
    for r in sorted_recs:
        k = tuple((r.get(f) or "") for f in key_fields)
        buckets.setdefault(k, []).append(r)

    grouped: list[dict] = []
    for k, items in buckets.items():
        # pick best scoring representative
        def _score(x: dict) -> float:
            try:
                return float(x.get("final_score", x.get("score", 0.0)) or 0.0)
            except Exception:
                return 0.0

        items_sorted = sorted(items, key=_score, reverse=True)
        rep = dict(items_sorted[0])  # shallow copy

        slot_ids = []
        unit_options = []
        for it in items_sorted:
            sid = it.get("slot_id")
            if sid is not None:
                slot_ids.append(sid)
            unit_options.append(
                {
                    "slot_id": sid,
                    "unit": it.get("unit"),
                    "floor": it.get("floor"),
                }
            )

        capacity_count = len(items_sorted)
        rep["capacity_count"] = capacity_count
        rep["slot_ids"] = slot_ids
        rep["unit_options"] = unit_options

        # Add a concise reason if capacity is aggregated
        if capacity_count > 1:
            reasons = rep.get("reasons")
            if isinstance(reasons, list):
                # keep it short; insert at front
                if "MULTI_CAPACITY" not in reasons:
                    rep["reasons"] = (["MULTI_CAPACITY"] + reasons)[:3]
            else:
                rep["reasons"] = ["MULTI_CAPACITY"]

        grouped.append(rep)

    # Preserve global ranking: sort groups by representative score
    grouped.sort(
        key=lambda x: float(x.get("final_score", x.get("score", 0.0)) or 0.0),
        reverse=True,
    )
    return grouped


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
                patient_ctx["scheduling_preferred_min_days"] = priority_profile.get("scheduling_preferred_min_days")
                patient_ctx["scheduling_preferred_max_days"] = priority_profile.get("scheduling_preferred_max_days")
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

    base_rows = cur.execute(sql, params).fetchall()
    conn.close()

    # Expand weekday patterns into concrete dates across allowed scheduling window
    rows = []
    if priority_profile and base_rows:
        min_days = int(patient_ctx.get("scheduling_window_min_days", 0) or 0)
        max_days = int(patient_ctx.get("scheduling_window_max_days", 21) or 21)
        for row in base_rows:
            weekday_fa = str(row["weekday_name"] or "").strip()
            weekday_py = FA_WEEKDAY_TO_PY.get(weekday_fa)
            if weekday_py is None:
                # If weekday cannot be mapped, keep row as-is without expansion
                rows.append(row)
                continue
            for d, days_ahead in _generate_dates_for_weekday_within_window(
                weekday_py,
                min_days,
                max_days,
            ):
                r = dict(row)
                r["_slot_date"] = d.strftime("%Y-%m-%d")
                r["_days_ahead"] = days_ahead
                rows.append(r)
    else:
        rows = list(base_rows)

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

        # Days ahead for this specific slot using concrete date if available
        slot_date = None
        days_ahead = None
        weekday_fa = str(row["weekday_name"] or "").strip()
        slot_date_str = row.get("_slot_date")
        if slot_date_str:
            slot_date = datetime.strptime(slot_date_str, "%Y-%m-%d").date()
            days_ahead = int(row.get("_days_ahead", (slot_date - _clinic_now().date()).days))
        else:
            weekday_py = FA_WEEKDAY_TO_PY.get(weekday_fa)
            if weekday_py is not None:
                slot_date_str = _next_occurrence_date(weekday_py)
                slot_date = datetime.strptime(slot_date_str, "%Y-%m-%d").date()
                days_ahead = (slot_date - _clinic_now().date()).days
        window_pref_score = (
            _window_preference_score(days_ahead, patient_ctx)
            if days_ahead is not None
            else 0.5
        )
        in_preferred = (window_pref_score >= 0.9)

        # Updated scoring formula including stronger window preference
        final_score = (
            0.30 * time_score +
            0.15 * financial_score +
            0.15 * patient_priority_score +
            0.10 * patient_value_score +
            0.20 * window_pref_score +
            0.05 * (1.0 if patient_ctx["in_followup_queue"] else 0.0) +
            0.03 * (1.0 if patient_ctx["in_scheduling_top300"] else 0.0) +
            0.02 * (1.0 if patient_ctx["financial_tier"] == "VIP"
                    else 0.5 if patient_ctx["financial_tier"] == "HIGH"
                    else 0.2 if patient_ctx["financial_tier"] == "MEDIUM"
                    else 0.0)
        )
        final_score = round(_clamp01(final_score), 3)

        # Concise, non-repetitive reasons (max 3) for receptionist UX
        reasons = []
        if in_preferred:
            reasons.append("IN_PREFERRED_WINDOW")
        else:
            # Outside preferred but inside allowed (since hard filter is applied)
            reasons.append("OUTSIDE_PREFERRED_BUT_ALLOWED")
        if patient_ctx.get("in_followup_queue"):
            reasons.append("FOLLOWUP_QUEUE")
        elif patient_ctx.get("in_scheduling_top300"):
            reasons.append("TOP_QUEUE")
        if doctor_id is not None:
            reasons.append("FILTERED_BY_DOCTOR")
        elif financial_score >= 0.7:
            reasons.append("INSURANCE_OK")
        # Cap reasons to 3
        reasons = reasons[:3]

        weekday_fa = str(row["weekday_name"] or "").strip()
        weekday_py = FA_WEEKDAY_TO_PY.get(weekday_fa)
        if isinstance(slot_date, (datetime, )):
            slot_date = slot_date.strftime("%Y-%m-%d")
        weekday_en = FA_WEEKDAY_TO_EN.get(weekday_fa) if weekday_fa else None

        # Always carry doctor metadata from the underlying slot when available.
        # preferred_doctor_filter flag is exposed separately in the response.
        rec_doctor_id = row["doctor_id"]
        rec_doctor_name = row["doctor_name"]
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
            "days_ahead": days_ahead,
            "in_preferred_window": in_preferred,
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
    # Collapse repeated same-date+time slots (multi-unit capacity) into one card.
    recommendations = _group_recommendations_by_datetime(recommendations)
    recommendations = _diversify_by_date(recommendations, k=TOP_N_RECOMMENDATIONS)
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
        # Keep this string in sync with the actual final_score computation above.
        "score_formula": (
            "0.30*time_score + 0.15*insurance_score + 0.15*patient_priority_score + "
            "0.10*patient_value_score + 0.20*window_preference_score + "
            "0.05*I(in_followup_queue) + 0.03*I(in_scheduling_top300) + "
            "tier_weight(financial_tier)"
        ),
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
    # NOTE: This override remains for historical reasons (the file evolved with
    # multiple hotfix layers). It must stay consistent with the primary
    # implementation above.

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
        # Resolve patient_id from record_no via master_patient_profile_v2
        patient_id = None
        try:
            pid_row = cur.execute(
                """
                SELECT patient_id
                FROM master_patient_profile_v2
                WHERE CAST(crm_patient_code AS TEXT) = CAST(? AS TEXT)
                LIMIT 1
                """,
                (rn,),
            ).fetchone()
            if not pid_row:
                try:
                    pid_row = cur.execute(
                        """
                        SELECT patient_id
                        FROM master_patient_profile_v2
                        WHERE CAST(record_no AS TEXT) = CAST(? AS TEXT)
                        LIMIT 1
                        """,
                        (rn,),
                    ).fetchone()
                except _sqlite3.OperationalError:
                    pid_row = None
            if pid_row and pid_row[0] is not None:
                try:
                    patient_id = int(pid_row[0])
                except Exception:
                    patient_id = None
        except _sqlite3.OperationalError:
            patient_id = None

        # Load final financial row by patient_id
        fin_row = None
        if patient_id is not None:
            try:
                fin_row = cur.execute(
                    """
                    SELECT
                        patient_id,
                        patient_value_score,
                        financial_tier,
                        lifetime_net_received_toman,
                        last_jalali_year
                    FROM patient_value_score_v2_final
                    WHERE patient_id = ?
                    LIMIT 1
                    """,
                    (patient_id,),
                ).fetchone()
            except _sqlite3.OperationalError:
                fin_row = None

        if fin_row:
            d = dict(fin_row)
            ctx["financial_tier"] = d.get("financial_tier")
            ctx["financial_value_score"] = d.get("patient_value_score")
            ctx["lifetime_net_received"] = d.get("lifetime_net_received_toman")
            ctx["last_payment_date_raw"] = None

        # Fallback for missing fields (legacy record_no-level)
        try:
            legacy = cur.execute(
                """
                SELECT
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
            legacy = None

        if legacy:
            ld = dict(legacy)
            if ctx["financial_tier"] is None:
                ctx["financial_tier"] = ld.get("financial_tier")
            if ctx["financial_value_score"] is None:
                ctx["financial_value_score"] = ld.get("financial_value_score")
            if ctx["lifetime_net_received"] is None:
                ctx["lifetime_net_received"] = ld.get("lifetime_net_received")
            if ctx["last_payment_date_raw"] is None:
                ctx["last_payment_date_raw"] = ld.get("last_payment_date_raw")

        # Follow-up queue membership
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

        # Scheduling queue (TOP300) membership
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
