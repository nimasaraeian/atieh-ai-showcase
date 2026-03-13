# -*- coding: utf-8 -*-
"""
Global patient search API – searches canonical mapped identity layer.

Endpoint:
  GET /patients/search?q=<query>&limit=50&offset=0

Canonical source: patient_recordno_map + record_no_patient_map.
These tables have record_no, patient_name_norm, phone_norm (real data, no UNKNOWN).
v_receptionist_search reads from mapping tables, NOT from v_financial_identity_profile or patients.

Fallback (if view missing): direct query on patient_recordno_map / record_no_patient_map.
"""
import os
import sqlite3
import logging
import re
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Same DB path as financial_operational
DB_PATH = os.environ.get("FINANCIAL_DB_PATH") or (
    "atieh_clinic_working.db"
    if os.path.exists("atieh_clinic_working.db")
    else "atieh_clinic.db"
)


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn, name: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='view' AND name=? LIMIT 1", (name,))
    return cur.fetchone() is not None


def _normalize_persian_text(s: str) -> str:
    """Normalize Persian/Arabic text for robust search."""
    if not s:
        return ""
    s = (
        s.replace("\u064a", "ی")
        .replace("\u0643", "ک")
        .replace("\u200c", " ")
    )
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _extract_digits(s: str) -> str:
    fa_to_en = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
    t = (s or "").translate(fa_to_en)
    return "".join(c for c in t if c.isdigit())


def search_patients(q: Optional[str], limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    """
    Receptionist-safe patient search.
    Returns only rows with valid record_no (exist in mapping tables).
    Prioritizes rows with real mobile.
    """
    raw_q = (q or "").strip()
    q_norm = _normalize_persian_text(raw_q)
    if not q_norm:
        return {"count": 0, "data": []}

    raw_tokens: List[str] = [t.strip() for t in q_norm.split(" ") if t and t.strip()]
    name_tokens: List[str] = [t for t in raw_tokens if len(t) >= 2]
    like = f"%{q_norm}%"
    q_digits = _extract_digits(q_norm)
    mobile_like = f"%{q_digits[-10:] if len(q_digits) >= 7 else q_digits}%" if len(q_digits) >= 5 else "%"

    conn = _get_conn()
    try:
        cur = conn.cursor()
        rows: List[Dict[str, Any]] = []
        seen_record_no: set = set()

        def build_where(prefix: str) -> tuple:
            """prefix: '' for patient_name/mobile, '_canonical' for patient_name_canonical/mobile_canonical."""
            w, p = [], []
            if q_digits:
                w.append("record_no LIKE ?")
                p.append(f"%{q_digits}%")
                if len(q_digits) >= 5:
                    w.append(
                        "REPLACE(REPLACE(REPLACE(COALESCE(mobile" + (f"_canonical" if prefix else "") + ",''),' ',''),'-',''),'۰','0') LIKE ?"
                    )
                    p.append(mobile_like)
            if name_tokens:
                col = "patient_name" + prefix
                token_clauses = [f"{col} LIKE ?" for _ in name_tokens]
                w.append("(" + " AND ".join(token_clauses) + ")")
                p.extend([f"%{t}%" for t in name_tokens])
            else:
                w.append("patient_name" + prefix + " LIKE ?")
                p.append(like)
            w.append("mobile" + prefix + " LIKE ?")
            p.append(like)
            return w, p

        where_receptionist, params_receptionist = build_where("")
        order_params = [q_norm, f"{q_norm}%", f"{q_norm}%"]

        # 1) Prefer v_receptionist_search (only selectable rows)
        use_receptionist_view = _table_exists(conn, "v_receptionist_search")
        if use_receptionist_view:
            try:
                cur.execute(
                    f"""
                    SELECT record_no, patient_name, mobile, financial_tier, lifetime_net_received, last_payment_date_raw
                    FROM v_receptionist_search
                    WHERE {" OR ".join(where_receptionist)}
                    ORDER BY
                        CASE WHEN record_no = ? THEN 0 WHEN record_no LIKE ? THEN 1 WHEN patient_name LIKE ? THEN 2 ELSE 3 END,
                        has_real_mobile DESC,
                        COALESCE(lifetime_net_received, 0) DESC
                    LIMIT ? OFFSET ?
                    """,
                    params_receptionist + order_params + [limit * 2, offset],
                )
                for r in cur.fetchall():
                    d = dict(r)
                    rn = (d.get("record_no") or "").strip()
                    if rn and rn not in seen_record_no:
                        seen_record_no.add(rn)
                        rows.append(d)
                        if len(rows) >= limit:
                            break
            except sqlite3.OperationalError as e:
                logger.warning("v_receptionist_search: %s", e)
                use_receptionist_view = False

        # 2) Fallback: patient_recordno_map directly (when view missing or needs more rows)
        if len(rows) < limit:
            try:
                w_prm = []
                p_prm: List[Any] = []
                if q_digits:
                    w_prm.append("prm.record_no LIKE ?")
                    p_prm.append(f"%{q_digits}%")
                    if len(q_digits) >= 5:
                        w_prm.append(
                            "REPLACE(REPLACE(COALESCE(prm.phone_norm,''),' ',''),'-','') LIKE ?"
                        )
                        p_prm.append(mobile_like)
                if name_tokens:
                    w_prm.append(
                        "(" + " AND ".join(["prm.patient_name_norm LIKE ?"] * len(name_tokens)) + ")"
                    )
                    p_prm.extend([f"%{t}%" for t in name_tokens])
                else:
                    w_prm.append("prm.patient_name_norm LIKE ?")
                    p_prm.append(like)
                w_prm.append("(prm.patient_name_norm LIKE ? OR prm.phone_norm LIKE ?)")
                p_prm.extend([like, like])

                cur.execute(
                    f"""
                    SELECT prm.record_no, prm.patient_name_norm AS patient_name, prm.phone_norm AS mobile,
                           fif.financial_tier, fif.lifetime_net_received, fif.last_payment_date_raw
                    FROM patient_recordno_map prm
                    LEFT JOIN financial_identity_profile fif ON fif.record_no = prm.record_no
                    WHERE {" OR ".join(w_prm)}
                      AND prm.record_no IS NOT NULL AND TRIM(prm.record_no) <> ''
                      AND prm.record_no <> '-' AND prm.record_no GLOB '[0-9]*'
                    ORDER BY
                      CASE WHEN prm.record_no = ? THEN 0 WHEN prm.record_no LIKE ? THEN 1
                           WHEN prm.patient_name_norm LIKE ? THEN 2 ELSE 3 END,
                      CASE WHEN prm.phone_norm NOT LIKE 'UNKNOWN%' AND prm.phone_norm IS NOT NULL THEN 1 ELSE 0 END DESC,
                      COALESCE(fif.lifetime_net_received, 0) DESC
                    LIMIT ?
                    """,
                    p_prm + order_params + [limit - len(rows) + 50],
                )
                for r in cur.fetchall():
                    d = dict(r)
                    rn = (d.get("record_no") or "").strip()
                    if not rn or rn in seen_record_no:
                        continue
                    seen_record_no.add(rn)
                    rows.append(d)
                    if len(rows) >= limit:
                        break
            except sqlite3.OperationalError as ex:
                logger.debug("patient_recordno_map fallback: %s", ex)

        # Enrich with in_top300, in_followup_queue
        for row in rows:
            rn = row.get("record_no")
            row["in_top300"] = False
            row["in_followup_queue"] = False
            if not rn:
                continue
            try:
                cur.execute(
                    "SELECT 1 FROM v_financial_scheduling_queue_top300 WHERE record_no = ? LIMIT 1",
                    (rn,),
                )
                if cur.fetchone():
                    row["in_top300"] = True
            except sqlite3.OperationalError:
                pass
            try:
                cur.execute(
                    "SELECT 1 FROM v_financial_followup_queue_contactable WHERE record_no = ? LIMIT 1",
                    (rn,),
                )
                if cur.fetchone():
                    row["in_followup_queue"] = True
            except sqlite3.OperationalError:
                pass

        return {"count": len(rows), "data": rows[:limit]}
    finally:
        conn.close()
