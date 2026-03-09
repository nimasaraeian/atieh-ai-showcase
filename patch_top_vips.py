from pathlib import Path
import re

path = Path(r".\app\api\financial_operational.py")
text = path.read_text(encoding="utf-8")

insert_block = r'''
@router.get("/top-vips")
def get_top_vips(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    Return top VIP financial identities ordered by revenue and score.
    """
    conn = get_financial_db()
    try:
        cur = conn.cursor()

        try:
            cur.execute("SELECT COUNT(*) FROM financial_identity_profile WHERE financial_tier = 'VIP'")
            total_count = cur.fetchone()[0]
        except sqlite3.OperationalError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Table financial_identity_profile not available: {e}",
            )

        cur.execute(
            """
            SELECT
                record_no,
                patient_name_canonical,
                financial_tier,
                lifetime_txn_count,
                lifetime_net_received,
                financial_value_score,
                recent_txn_count,
                recent_net_received,
                last_payment_date_raw
            FROM financial_identity_profile
            WHERE financial_tier = 'VIP'
            ORDER BY financial_value_score DESC, lifetime_net_received DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        rows = cur.fetchall()

        return {
            "count": total_count,
            "limit": limit,
            "offset": offset,
            "data": [dict(r) for r in rows],
        }
    finally:
        conn.close()


'''

marker = r'(?=@router\.get\("/scheduling/priority"\))'

if re.search(r'@router\.get\("/top-vips"\)', text):
    raise SystemExit("top-vips already exists.")

new_text, count = re.subn(marker, insert_block, text, count=1)
if count != 1:
    raise SystemExit(f"Insertion failed. Matched markers: {count}")

path.write_text(new_text, encoding="utf-8")
print("Inserted /top-vips successfully.")
