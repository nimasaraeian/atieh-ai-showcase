# -*- coding: utf-8 -*-
"""
Reception patient search service – V2 payments-first identity layer.

Uses: master_patient_profile_v2, payment_identity_master, patient_master_link_v2,
patients_identity_normalized. Read-only. Same DB as financial (atieh_clinic_recovery81_test.db).
"""
import logging
import os
import re
import sqlite3
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Same DB path as financial_operational
DB_PATH = os.environ.get("FINANCIAL_DB_PATH") or (
    "atieh_clinic_recovery81_test.db"
    if os.path.exists("atieh_clinic_recovery81_test.db")
    else "atieh_clinic_working.db"
    if os.path.exists("atieh_clinic_working.db")
    else "atieh_clinic.db"
)

# Columns matching reception_patient_search_view (from master_patient_profile_v2)
VIEW_COLUMNS = (
    "patient_id", "crm_patient_code", "patient_name_canonical", "patient_name_key",
    "primary_phone", "national_id_norm", "payment_rows_count", "total_net_received",
    "positive_net_received_sum", "negative_net_received_sum", "first_year", "last_year",
    "identity_strength_tier", "link_tier", "link_rule", "review_flag", "review_reason", "created_at"
)
TABLE = "master_patient_profile_v2"
STAGING_TABLE = "payments_unified_staging"
INSURANCE_VIEW_V2 = "patient_insurance_profile_v2"


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _digits_only(s: str) -> str:
    if not s:
        return ""
    fa = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
    return "".join(c for c in (s or "").translate(fa) if c.isdigit())


def _normalize_phone_for_search(raw: str) -> str:
    """Normalize to 11-digit 09xxxxxxxxx for exact match, or last 10 digits for LIKE."""
    d = _digits_only(raw)
    if not d:
        return ""
    if d.startswith("98") and len(d) >= 10:
        d = d[2:]
    if len(d) == 10 and d.startswith("9"):
        d = "0" + d
    if len(d) > 11:
        d = d[-11:]
    return d


def _row_to_payload(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    # Build structured response: identity summary, financial summary, confidence, review warning, linked crm code(s).
    # Include aliases for reception view: canonical_patient_name, primary_phone_norm, canonical_national_id_norm.
    return {
        "patient_id": d.get("patient_id"),
        "crm_patient_code": d.get("crm_patient_code"),
        "patient_name_canonical": d.get("patient_name_canonical"),
        "canonical_patient_name": d.get("patient_name_canonical"),
        "patient_name_key": d.get("patient_name_key"),
        "primary_phone": d.get("primary_phone"),
        "primary_phone_norm": d.get("primary_phone"),
        "national_id_norm": d.get("national_id_norm"),
        "canonical_national_id_norm": d.get("national_id_norm"),
        "payment_rows_count": d.get("payment_rows_count"),
        "total_net_received": d.get("total_net_received"),
        "positive_net_received_sum": d.get("positive_net_received_sum"),
        "negative_net_received_sum": d.get("negative_net_received_sum"),
        "first_year": d.get("first_year"),
        "last_year": d.get("last_year"),
        "identity_strength_tier": d.get("identity_strength_tier"),
        "link_tier": d.get("link_tier"),
        "link_rule": d.get("link_rule"),
        "review_flag": d.get("review_flag"),
        "review_reason": d.get("review_reason"),
        "created_at": d.get("created_at"),
        "identity_summary": {
            "name": d.get("patient_name_canonical"),
            "name_key": d.get("patient_name_key"),
            "primary_phone": d.get("primary_phone"),
            "national_id_norm": d.get("national_id_norm"),
        },
        "financial_summary": {
            "payment_rows_count": d.get("payment_rows_count"),
            "total_net_received": d.get("total_net_received"),
            "positive_net_received_sum": d.get("positive_net_received_sum"),
            "negative_net_received_sum": d.get("negative_net_received_sum"),
            "first_year": d.get("first_year"),
            "last_year": d.get("last_year"),
        },
        "confidence": {
            "link_tier": d.get("link_tier"),
            "link_rule": d.get("link_rule"),
            "identity_strength_tier": d.get("identity_strength_tier"),
        },
        "review_warning": _needs_review(d.get("review_flag"), d.get("review_reason")),
        "review_reason": d.get("review_reason"),
        "linked_crm_codes": [d.get("crm_patient_code")] if d.get("crm_patient_code") else [],
        "amounts_unit": "IRR",
        "display_total_net_received_irr": _format_rial(d.get("total_net_received")),
        "display_positive_sum_irr": _format_rial(d.get("positive_net_received_sum")),
        "display_negative_sum_irr": _format_rial(d.get("negative_net_received_sum")),
    }


def _format_rial(val: Any) -> str | None:
    """Format numeric value for display as Rial (thousand separators). Returns None if not a number."""
    if val is None:
        return None
    try:
        n = float(val)
        if n != n:
            return None
        return f"{n:,.0f}".replace(",", "\u2009")
    except (TypeError, ValueError):
        return None


def _needs_review(review_flag: Any, review_reason: Any) -> bool:
    """Show review warning only when review_flag=1 OR review_reason is non-empty."""
    if review_flag == 1:
        return True
    if review_reason is None:
        return False
    return bool(str(review_reason).strip())


def _normalize_insurer_display(raw: Optional[str]) -> Optional[str]:
    """Simple normalization: remove numbers, remove parentheses, trim. e.g. تامين اجتماعي(3) -> تامین اجتماعی, اسيا10% -> آسیا."""
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip()
    if not s:
        return None
    s = re.sub(r"[0-9۰-۹]+", "", s)
    s = re.sub(r"[()]", "", s)
    s = re.sub(r"%\s*", "", s)
    s = s.strip()
    return s if s else None


def _get_insurance_profile(conn: sqlite3.Connection, crm_patient_code: Optional[str]) -> Optional[dict[str, Any]]:
    """Return patient_insurance_profile_v2 row for crm_patient_code; normalize insurer names. None if view missing or not found."""
    if not crm_patient_code or not str(crm_patient_code).strip():
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            f"SELECT crm_patient_code, most_recent_insurer, most_frequent_insurer, distinct_insurers_count, payment_rows_count FROM {INSURANCE_VIEW_V2} WHERE crm_patient_code = ?",
            (str(crm_patient_code).strip(),),
        )
        row = cur.fetchone()
        if not row:
            return None
        most_recent_raw = row[1]
        most_frequent_raw = row[2]
        distinct_count = row[3] or 0
        payment_rows_count = row[4] or 0
        insurance_recent = _normalize_insurer_display(most_recent_raw) or _normalize_insurer_display(most_frequent_raw)
        insurance_primary = _normalize_insurer_display(most_frequent_raw) or _normalize_insurer_display(most_recent_raw)
        return {
            "crm_patient_code": row[0],
            "most_recent_insurer": most_recent_raw,
            "most_frequent_insurer": most_frequent_raw,
            "insurance_recent": insurance_recent,
            "insurance_primary": insurance_primary,
            "insurance_variants_count": distinct_count,
            "distinct_insurers_count": distinct_count,
            "payment_rows_count": payment_rows_count,
        }
    except sqlite3.OperationalError:
        return None


def _get_visit_dates_from_payments(
    conn: sqlite3.Connection, crm_codes: list[str]
) -> tuple[Optional[str], Optional[str]]:
    """
    Derive first_visit_date and last_payment_date from payments_unified_staging.
    first_visit_date = MIN(appointment_date_raw); if all null, use MIN(shamsi_year) as year string.
    last_payment_date = MAX(appointment_date_raw).
    Returns (first_visit_date, last_payment_date); either may be None.
    """
    codes = [c for c in (crm_codes or []) if c is not None and str(c).strip()]
    if not codes:
        return (None, None)
    placeholders = ",".join("?" * len(codes))
    cur = conn.cursor()
    # Last payment: MAX(appointment_date_raw)
    cur.execute(
        f"SELECT MAX(appointment_date_raw) FROM {STAGING_TABLE} WHERE record_no IN ({placeholders}) AND TRIM(COALESCE(appointment_date_raw, '')) != ''",
        codes,
    )
    last_row = cur.fetchone()
    last_payment_date = (last_row[0] or "").strip() or None
    # First visit: MIN(appointment_date_raw); if none, fallback MIN(shamsi_year)
    cur.execute(
        f"SELECT MIN(appointment_date_raw) FROM {STAGING_TABLE} WHERE record_no IN ({placeholders}) AND TRIM(COALESCE(appointment_date_raw, '')) != ''",
        codes,
    )
    first_row = cur.fetchone()
    first_visit_date = (first_row[0] or "").strip() or None
    if first_visit_date is None:
        cur.execute(
            f"SELECT MIN(shamsi_year) FROM {STAGING_TABLE} WHERE record_no IN ({placeholders}) AND shamsi_year IS NOT NULL",
            codes,
        )
        year_row = cur.fetchone()
        if year_row and year_row[0] is not None:
            first_visit_date = str(year_row[0])
    return (first_visit_date, last_payment_date)


def _patient_ids_with_multiple_crm(conn: sqlite3.Connection, patient_ids: list[int]) -> set[int]:
    """Return set of patient_id that have more than one crm_patient_code in master_patient_profile_v2."""
    if not patient_ids:
        return set()
    placeholders = ",".join("?" * len(patient_ids))
    cur = conn.cursor()
    cur.execute(
        f"SELECT patient_id FROM {TABLE} WHERE patient_id IN ({placeholders}) GROUP BY patient_id HAVING COUNT(*) > 1",
        patient_ids,
    )
    return {row[0] for row in cur.fetchall()}


def search_reception_patient(
    q: Optional[str],
    limit: int = 50,
    offset: int = 0,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    """
    Search by patient name, phone, crm code, or patient_id.
    Returns top page_size results (default 50), sorted by relevance then tier/count/year.
    Pagination: offset = (page - 1) * page_size; limit = page_size.
    """
    raw = (q or "").strip()
    if not raw:
        return {"count": 0, "data": [], "query": q, "page": page, "page_size": page_size, "total_pages": 0}

    actual_limit = min(max(1, page_size), 200)
    actual_offset = max(0, (page - 1) * actual_limit)

    conn = _get_db()
    try:
        cur = conn.cursor()
        cols = ", ".join(VIEW_COLUMNS)
        params: list = []
        conditions: list = []

        digits = _digits_only(raw)
        if digits.isdigit():
            conditions.append("(patient_id = ?)")
            params.append(int(digits))
        conditions.append("(crm_patient_code = ? OR crm_patient_code LIKE ?)")
        params.extend([raw.strip(), f"%{raw.strip()}%"])
        like_arg = f"%{raw}%"
        conditions.append("(patient_name_canonical LIKE ? OR patient_name_key LIKE ?)")
        params.extend([like_arg, like_arg])
        phone_norm = _normalize_phone_for_search(raw)
        if phone_norm:
            conditions.append("(primary_phone = ? OR primary_phone LIKE ?)")
            params.extend([phone_norm, f"%{phone_norm}%"])
        if len(digits) == 10:
            conditions.append("(national_id_norm = ?)")
            params.append(digits)

        where = " OR ".join(conditions)
        count_sql = f"SELECT COUNT(*) FROM {TABLE} WHERE {where}"
        cur.execute(count_sql, params)
        total = cur.fetchone()[0]

        # Sort: exact crm, exact phone, exact name, then link_tier (A first), payment_rows_count DESC, last_year DESC
        order_params = [raw.strip(), phone_norm or "", raw.strip(), raw.strip()]
        order_sql = (
            f" ORDER BY "
            f"(CASE WHEN crm_patient_code = ? THEN 0 ELSE 1 END), "
            f"(CASE WHEN primary_phone = ? THEN 0 ELSE 1 END), "
            f"(CASE WHEN patient_name_canonical = ? OR patient_name_key = ? THEN 0 ELSE 1 END), "
            f"(CASE link_tier WHEN 'A' THEN 4 WHEN 'B' THEN 3 WHEN 'C' THEN 2 WHEN 'D' THEN 1 ELSE 0 END) DESC, "
            f"payment_rows_count DESC, COALESCE(last_year, 0) DESC "
            f"LIMIT ? OFFSET ?"
        )
        sql = f"SELECT {cols} FROM {TABLE} WHERE {where}{order_sql}"
        cur.execute(sql, params + order_params + [actual_limit, actual_offset])
        rows = cur.fetchall()

        data = [_row_to_payload(r) for r in rows]
        patient_ids = list({r["patient_id"] for r in data if r.get("patient_id") is not None})
        multi_crm_ids = _patient_ids_with_multiple_crm(conn, patient_ids)
        for r in data:
            r["multi_crm_for_same_patient_flag"] = r.get("patient_id") in multi_crm_ids

        total_pages = (total + actual_limit - 1) // actual_limit if actual_limit else 0
        return {
            "count": total,
            "data": data,
            "query": q,
            "page": page,
            "page_size": actual_limit,
            "total_pages": total_pages,
        }
    finally:
        conn.close()


def get_reception_patient_by_id(patient_id: int) -> dict[str, Any]:
    """
    All profiles linked to this patient_id.
    Includes identity summary, financial summary, review status, linked_crm_codes (all),
    years covered, payment_rows_count, value band. multi_crm_for_same_patient_flag when count > 1.
    """
    conn = _get_db()
    try:
        cur = conn.cursor()
        cols = ", ".join(VIEW_COLUMNS)
        cur.execute(f"SELECT {cols} FROM {TABLE} WHERE patient_id = ? ORDER BY payment_rows_count DESC", (patient_id,))
        rows = cur.fetchall()
        data = [_row_to_payload(r) for r in rows]
        linked_crm_codes = list({r.get("crm_patient_code") for r in data if r.get("crm_patient_code")})
        multi_crm = len(data) > 1
        for r in data:
            r["multi_crm_for_same_patient_flag"] = multi_crm
            r["linked_crm_codes"] = linked_crm_codes
        first_visit_date, last_payment_date = _get_visit_dates_from_payments(conn, linked_crm_codes)
        for r in data:
            r["first_visit_date"] = first_visit_date
            r["last_payment_date"] = last_payment_date
            ins = _get_insurance_profile(conn, r.get("crm_patient_code"))
            r["insurance_profile"] = ins
            r["insurance_primary"] = ins.get("insurance_primary") if ins else None
            r["insurance_recent"] = ins.get("insurance_recent") if ins else None
            r["insurance_variants_count"] = (ins.get("insurance_variants_count") or 0) if ins else 0
            r["display_insurer"] = (ins.get("insurance_recent") or ins.get("insurance_primary")) if ins else None
            r["multiple_insurers"] = ((ins.get("insurance_variants_count") or 0) > 1) if ins else False
        # Aggregate for single-patient view: first profile as primary, with combined summary
        primary = data[0] if data else None
        total_payment_rows = sum(r.get("payment_rows_count") or 0 for r in data)
        total_net = sum(r.get("total_net_received") or 0 for r in data)
        years = set()
        for r in data:
            if r.get("first_year") is not None:
                years.add(r["first_year"])
            if r.get("last_year") is not None:
                years.add(r["last_year"])

        response = {
            "patient_id": patient_id,
            "profiles": data,
            "count": len(data),
            "multi_crm_for_same_patient_flag": multi_crm,
            "linked_crm_codes": linked_crm_codes,
            "first_visit_date": first_visit_date,
            "last_payment_date": last_payment_date,
            "identity_summary": primary.get("identity_summary") if primary else None,
            "financial_summary": {
                "payment_rows_count": total_payment_rows,
                "total_net_received": total_net,
                "first_year": min(years) if years else None,
                "last_year": max(years) if years else None,
                "first_visit_date": first_visit_date,
                "last_payment_date": last_payment_date,
            } if data else None,
            "review_status": {
                "review_warning": any(r.get("review_warning") for r in data),
                "review_reason": primary.get("review_reason") if primary and multi_crm else (primary.get("review_reason") if primary else None),
            },
            "years_covered": sorted(years) if years else [],
            "value_band": primary.get("link_tier") if primary else None,
            "insurance_primary": primary.get("insurance_primary") if primary else None,
            "insurance_recent": primary.get("insurance_recent") if primary else None,
            "insurance_variants_count": primary.get("insurance_variants_count") if primary else 0,
            "display_insurer": primary.get("display_insurer") if primary else None,
            "multiple_insurers": primary.get("multiple_insurers") if primary else False,
            "insurance_profile": primary.get("insurance_profile") if primary else None,
        }
        try:
            from app.engine.patient_priority import get_patient_priority_profile
            crm = linked_crm_codes[0] if linked_crm_codes else None
            if crm or patient_id:
                pri = get_patient_priority_profile(crm_patient_code=crm, patient_id=patient_id)
                if pri:
                    response["patient_priority_profile"] = pri
        except Exception as e:
            logger.debug("Patient priority profile not attached: %s", e)
        return response
    finally:
        conn.close()


def get_reception_patient_by_crm_code(crm_code: str) -> dict[str, Any]:
    """Single profile by crm_patient_code (unique). Includes first_visit_date and last_payment_date from payments."""
    conn = _get_db()
    try:
        cur = conn.cursor()
        cols = ", ".join(VIEW_COLUMNS)
        cur.execute(f"SELECT {cols} FROM {TABLE} WHERE crm_patient_code = ?", (crm_code.strip(),))
        row = cur.fetchone()
        if not row:
            return {"crm_patient_code": crm_code.strip(), "profile": None, "found": False}
        profile = _row_to_payload(row)
        first_visit_date, last_payment_date = _get_visit_dates_from_payments(conn, [crm_code.strip()])
        profile["first_visit_date"] = first_visit_date
        profile["last_payment_date"] = last_payment_date
        ins = _get_insurance_profile(conn, crm_code.strip())
        profile["insurance_profile"] = ins
        profile["insurance_primary"] = ins.get("insurance_primary") if ins else None
        profile["insurance_recent"] = ins.get("insurance_recent") if ins else None
        profile["insurance_variants_count"] = (ins.get("insurance_variants_count") or 0) if ins else 0
        profile["display_insurer"] = (ins.get("insurance_recent") or ins.get("insurance_primary")) if ins else None
        profile["multiple_insurers"] = ((ins.get("insurance_variants_count") or 0) > 1) if ins else False
        out = {
            "crm_patient_code": crm_code.strip(),
            "profile": profile,
            "found": True,
            "first_visit_date": first_visit_date,
            "last_payment_date": last_payment_date,
            "insurance_primary": profile.get("insurance_primary"),
            "insurance_recent": profile.get("insurance_recent"),
            "insurance_variants_count": profile.get("insurance_variants_count"),
            "display_insurer": profile.get("display_insurer"),
            "multiple_insurers": profile.get("multiple_insurers"),
            "insurance_profile": ins,
        }
        try:
            from app.engine.patient_priority import get_patient_priority_profile
            pri = get_patient_priority_profile(crm_patient_code=crm_code.strip())
            if pri:
                out["patient_priority_profile"] = pri
        except Exception as e:
            logger.debug("Patient priority profile not attached: %s", e)
        return out
    finally:
        conn.close()
