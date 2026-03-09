from pathlib import Path
import re

path = Path(r".\app\api\financial_operational.py")
text = path.read_text(encoding="utf-8")

insert_block = r'''
@router.get("/patient/{record_no}")
def get_financial_patient_detail(record_no: str):
    """
    Return financial and operational detail for a single financial identity.
    """
    conn = get_financial_db()
    try:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                record_no,
                financial_tier,
                financial_value_score,
                lifetime_txn_count,
                lifetime_net_received,
                lifetime_patient_paid,
                lifetime_insurer_paid,
                lifetime_negative_net,
                lifetime_negative_txn_count,
                first_payment_date_raw,
                last_payment_date_raw,
                cash_txn_count,
                insurance_txn_count,
                recent_txn_count,
                recent_net_received,
                has_date_range
            FROM financial_identity_profile
            WHERE record_no = ?
            """,
            (record_no,),
        )
        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"record_no not found: {record_no}")

        profile = dict(row)

        # Follow-up membership
        in_followup_queue = False
        followup_action_type = None
        try:
            cur.execute(
                """
                SELECT action_type
                FROM v_financial_followup_queue_contactable
                WHERE record_no = ?
                LIMIT 1
                """,
                (record_no,),
            )
            f_row = cur.fetchone()
            if f_row:
                in_followup_queue = True
                followup_action_type = f_row[0]
        except sqlite3.OperationalError:
            pass

        # Scheduling membership
        in_scheduling_top300 = False
        scheduling_band = None
        scheduling_priority_score = None
        try:
            cur.execute(
                """
                SELECT scheduling_band, scheduling_priority_score
                FROM v_financial_scheduling_queue_top300
                WHERE record_no = ?
                LIMIT 1
                """,
                (record_no,),
            )
            s_row = cur.fetchone()
            if s_row:
                in_scheduling_top300 = True
                scheduling_band = s_row[0]
                scheduling_priority_score = s_row[1]
        except sqlite3.OperationalError:
            pass

        return {
            "record_no": record_no,
            "financial_profile": profile,
            "operational_status": {
                "in_followup_queue": in_followup_queue,
                "followup_action_type": followup_action_type,
                "in_scheduling_top300": in_scheduling_top300,
                "scheduling_band": scheduling_band,
                "scheduling_priority_score": scheduling_priority_score,
            },
        }
    finally:
        conn.close()


'''

marker = r'(?=@router\.get\("/scheduling/priority"\))'

if re.search(r'@router\.get\("/patient/\{record_no\}"\)', text):
    raise SystemExit("patient/{record_no} already exists.")

new_text, count = re.subn(marker, insert_block, text, count=1)
if count != 1:
    raise SystemExit(f"Insertion failed. Matched markers: {count}")

path.write_text(new_text, encoding="utf-8")
print("Inserted /patient/{record_no} successfully.")
