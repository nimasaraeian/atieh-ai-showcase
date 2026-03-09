from pathlib import Path
import re

path = Path(r".\app\api\financial_operational.py")
text = path.read_text(encoding="utf-8")

pattern = r'''@router\.get\("/patient-lookup"\)\s*
def get_patient_financial_lookup\(
.*?
(?=\n# .*Test / status route)'''

replacement = '''@router.get("/patient-lookup")
def get_patient_financial_lookup(
    q: Optional[str] = Query(None, description="Generic search: record_no, mobile, patient name"),
    mobile: Optional[str] = Query(None),
    record_no: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    Flexible patient lookup for frontend search and appointment workflow.

    Supports:
    - q: generic search over record_no / mobile / patient_name
    - mobile: direct mobile lookup
    - record_no: direct record lookup
    """
    if not q and not mobile and not record_no:
        return {"count": 0, "data": []}

    conn = get_financial_db()
    try:
        cur = conn.cursor()

        rows = []
        seen = set()

        def add_rows(fetched):
            for r in fetched:
                d = dict(r)
                key = str(d.get("record_no") or "")
                if key not in seen:
                    seen.add(key)
                    rows.append(d)

        # 1) explicit record_no lookup
        if record_no:
            try:
                cur.execute(
                    """
                    SELECT
                        record_no,
                        patient_name_canonical,
                        mobile_canonical,
                        financial_tier,
                        action_type,
                        scheduling_band,
                        scheduling_priority_score,
                        lifetime_net_received,
                        last_payment_date_raw
                    FROM v_financial_scheduling_queue_top300
                    WHERE record_no = ?
                    LIMIT ? OFFSET ?
                    """,
                    (str(record_no), limit, offset),
                )
                add_rows(cur.fetchall())
            except sqlite3.OperationalError:
                pass

        # 2) explicit mobile lookup
        if mobile:
            mobile_clean = "".join(c for c in str(mobile) if c.isdigit())
            if len(mobile_clean) >= 7:
                try:
                    cur.execute(
                        """
                        SELECT
                            record_no,
                            patient_name_canonical,
                            mobile_canonical,
                            financial_tier,
                            action_type,
                            scheduling_band,
                            scheduling_priority_score,
                            lifetime_net_received,
                            last_payment_date_raw
                        FROM v_financial_scheduling_queue_top300
                        WHERE REPLACE(REPLACE(mobile_canonical,' ',''),'-','') LIKE ?
                        LIMIT ? OFFSET ?
                        """,
                        (f"%{mobile_clean[-10:]}%", limit, offset),
                    )
                    add_rows(cur.fetchall())
                except sqlite3.OperationalError:
                    pass

                if not rows:
                    try:
                        cur.execute(
                            """
                            SELECT
                                record_no,
                                patient_name_canonical,
                                mobile_canonical,
                                financial_tier,
                                action_type,
                                NULL as scheduling_band,
                                action_priority_score as scheduling_priority_score,
                                lifetime_net_received,
                                last_payment_date_raw
                            FROM v_financial_followup_daily_balanced
                            WHERE REPLACE(REPLACE(mobile_canonical,' ',''),'-','') LIKE ?
                            LIMIT ? OFFSET ?
                            """,
                            (f"%{mobile_clean[-10:]}%", limit, offset),
                        )
                        add_rows(cur.fetchall())
                    except sqlite3.OperationalError:
                        pass

        # 3) generic q lookup
        if q:
            q_str = str(q).strip()
            q_digits = "".join(c for c in q_str if c.isdigit())

            # 3a) q as record_no
            if q_digits:
                try:
                    cur.execute(
                        """
                        SELECT
                            record_no,
                            patient_name_canonical,
                            mobile_canonical,
                            financial_tier,
                            action_type,
                            scheduling_band,
                            scheduling_priority_score,
                            lifetime_net_received,
                            last_payment_date_raw
                        FROM v_financial_scheduling_queue_top300
                        WHERE CAST(record_no AS TEXT) LIKE ?
                        LIMIT ? OFFSET ?
                        """,
                        (f"%{q_digits}%", limit, offset),
                    )
                    add_rows(cur.fetchall())
                except sqlite3.OperationalError:
                    pass

            # 3b) q as mobile fragment
            if q_digits and len(q_digits) >= 7:
                try:
                    cur.execute(
                        """
                        SELECT
                            record_no,
                            patient_name_canonical,
                            mobile_canonical,
                            financial_tier,
                            action_type,
                            scheduling_band,
                            scheduling_priority_score,
                            lifetime_net_received,
                            last_payment_date_raw
                        FROM v_financial_scheduling_queue_top300
                        WHERE REPLACE(REPLACE(mobile_canonical,' ',''),'-','') LIKE ?
                        LIMIT ? OFFSET ?
                        """,
                        (f"%{q_digits[-10:]}%", limit, offset),
                    )
                    add_rows(cur.fetchall())
                except sqlite3.OperationalError:
                    pass

            # 3c) q as patient name
            try:
                cur.execute(
                    """
                    SELECT
                        record_no,
                        patient_name_canonical,
                        mobile_canonical,
                        financial_tier,
                        action_type,
                        scheduling_band,
                        scheduling_priority_score,
                        lifetime_net_received,
                        last_payment_date_raw
                    FROM v_financial_scheduling_queue_top300
                    WHERE patient_name_canonical LIKE ?
                    LIMIT ? OFFSET ?
                    """,
                    (f"%{q_str}%", limit, offset),
                )
                add_rows(cur.fetchall())
            except sqlite3.OperationalError:
                pass

            if not rows:
                try:
                    cur.execute(
                        """
                        SELECT
                            record_no,
                            patient_name_canonical,
                            mobile_canonical,
                            financial_tier,
                            action_type,
                            NULL as scheduling_band,
                            action_priority_score as scheduling_priority_score,
                            lifetime_net_received,
                            last_payment_date_raw
                        FROM v_financial_followup_daily_balanced
                        WHERE patient_name_canonical LIKE ?
                        LIMIT ? OFFSET ?
                        """,
                        (f"%{q_str}%", limit, offset),
                    )
                    add_rows(cur.fetchall())
                except sqlite3.OperationalError:
                    pass

        return {
            "count": len(rows),
            "data": rows[0:limit],
        }
    finally:
        conn.close()


'''

new_text, count = re.subn(pattern, replacement, text, flags=re.DOTALL)
if count != 1:
    raise SystemExit(f"Replacement failed. Matched blocks: {count}")

path.write_text(new_text, encoding="utf-8")
print("Patched /patient-lookup successfully.")
