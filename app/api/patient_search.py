# -*- coding: utf-8 -*-
"""
Global patient search API – searches across full patient dataset.

Endpoint:
  GET /patients/search?q=<query>&limit=50&offset=0

Sources:
  - v_financial_identity_profile (record_no + name + mobile + financial data)
  - patients + patient_recordno_map (patients without financial profile)
  - appointment_recordno_bridge (record_nos from appointment files)

Enrichment: in_top300, in_followup_queue from operational views.
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


def _extract_digits(s: str) -> str:
    """Extract digits from string (ASCII + Persian) for numeric search."""
    fa_to_en = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
    t = (s or "").translate(fa_to_en)
    return "".join(c for c in t if c.isdigit())


def search_patients(q: Optional[str], limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    """
    Global patient search: v_financial_identity_profile + patients fallback.
    Returns: { count, data: [ { record_no, patient_name, mobile, financial_tier,
              lifetime_net_received, last_payment_date_raw, in_top300, in_followup_queue } ] }
    """
    q = (q or "").strip()
    if not q:
        return {"count": 0, "data": []}

    # Tokenize the query for order-insensitive name search (e.g. "رضایی علیرضا" vs "علیرضا رضایی")
    # Filter tokens with length >= 2 to avoid single-char noise (e.g. "ا" matching too broadly)
    raw_tokens: List[str] = [t.strip() for t in re.split(r"\s+", q) if t and t.strip()]
    name_tokens: List[str] = [t for t in raw_tokens if len(t) >= 2]

    conn = _get_conn()
    try:
        cur = conn.cursor()
        rows: List[Dict[str, Any]] = []
        seen_record_no: set = set()
        seen_patient_key: set = set()

        # 1) Search v_financial_identity_profile (main source - 128K identities with financial data)
        like = f"%{q}%"
        q_digits = _extract_digits(q)
        mobile_like = f"%{q_digits[-10:] if len(q_digits) >= 7 else q_digits}%" if len(q_digits) >= 5 else "%"

        try:
            where_parts = []
            params: List[Any] = []

            # Numeric / record_no / mobile search (unchanged)
            if q_digits:
                where_parts.append("record_no LIKE ?")
                params.append(f"%{q_digits}%")
                if len(q_digits) >= 5:
                    where_parts.append(
                        "REPLACE(REPLACE(REPLACE(COALESCE(mobile_canonical,''),' ',''),'-',''),'۰','0') LIKE ?"
                    )
                    params.append(mobile_like)

            # Name search: all tokens must match somewhere in patient_name_canonical (order-insensitive)
            if name_tokens:
                token_clauses = []
                for token in name_tokens:
                    token_clauses.append("patient_name_canonical LIKE ?")
                    params.append(f"%{token}%")
                where_parts.append("(" + " AND ".join(token_clauses) + ")")
            else:
                where_parts.append("patient_name_canonical LIKE ?")
                params.append(like)

            # Fallback mobile LIKE with original query text
            where_parts.append("mobile_canonical LIKE ?")
            params.append(like)

            where_sql = " OR ".join(where_parts)

            sql = f"""
                SELECT
                    record_no,
                    patient_name_canonical AS patient_name,
                    mobile_canonical AS mobile,
                    financial_tier,
                    lifetime_net_received,
                    last_payment_date_raw
                FROM v_financial_identity_profile
                WHERE {where_sql}
                ORDER BY
                    CASE WHEN record_no = ? THEN 0
                         WHEN record_no LIKE ? THEN 1
                         WHEN patient_name_canonical LIKE ? THEN 2
                         ELSE 3 END,
                    COALESCE(lifetime_net_received, 0) DESC
                LIMIT ? OFFSET ?
            """
            params.extend([q.strip(), f"{q.strip()}%", f"{q.strip()}%", limit * 2, offset])

            cur.execute(sql, params)
            for r in cur.fetchall():
                d = dict(r)
                rn = d.get("record_no")
                if rn and rn not in seen_record_no:
                    seen_record_no.add(rn)
                    rows.append(d)
        except sqlite3.OperationalError as e:
            logger.warning("v_financial_identity_profile search: %s", e)

        # 2) Fallback: patients + patient_recordno_map (patients not in financial profile)
        if len(rows) < limit and q.strip():
            try:
                # Build an order-insensitive token-based name search for patients.name
                name_where_clauses: List[str] = []
                name_params: List[Any] = []

                if name_tokens:
                    # Require all tokens to be present in the name (AND of LIKEs)
                    name_where_clauses.append(
                        "(" + " AND ".join(["p.name LIKE ?"] * len(name_tokens)) + ")"
                    )
                    name_params.extend([f"%{token}%" for token in name_tokens])
                else:
                    name_where_clauses.append("p.name LIKE ?")
                    name_params.append(like)

                # Also allow phone substring search (use original LIKE pattern)
                name_where_clauses.append("p.phone LIKE ?")
                name_params.append(like)

                where_sql = " OR ".join(name_where_clauses)

                sql = f"""
                    SELECT
                        prm.record_no,
                        p.name AS patient_name,
                        COALESCE(prm.phone_norm, p.phone) AS mobile
                    FROM patients p
                    LEFT JOIN patient_recordno_map prm ON prm.patient_id = p.id
                    WHERE {where_sql}
                    ORDER BY p.id DESC
                    LIMIT ?
                """
                params = name_params + [limit - len(rows) + 50]

                cur.execute(sql, params)
                for r in cur.fetchall():
                    d = dict(r)
                    rn = (d.get("record_no") or "").strip() if d.get("record_no") else ""
                    if rn and rn in seen_record_no:
                        continue
                    pk = f"{d.get('patient_name','')}|{d.get('mobile','')}"
                    if pk in seen_patient_key:
                        continue
                    if rn:
                        seen_record_no.add(rn)
                    seen_patient_key.add(pk)
                    d["record_no"] = rn or None
                    d["financial_tier"] = None
                    d["lifetime_net_received"] = None
                    d["last_payment_date_raw"] = None
                    rows.append(d)
                    if len(rows) >= limit:
                        break
            except sqlite3.OperationalError as ex:
                logger.debug("patients fallback: %s", ex)

        # 3) Enrich with in_top300, in_followup_queue
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
