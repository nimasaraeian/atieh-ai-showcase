from pathlib import Path
import re

path = Path(r".\app\api\financial_operational.py")
text = path.read_text(encoding="utf-8")

insert_block = r'''
@router.get("/dashboard/trends")
def get_dashboard_trends(
    limit: int = Query(24, ge=1, le=120),
):
    """
    Return monthly trend summary based on last_payment_date_raw.
    """
    conn = get_financial_db()
    try:
        cur = conn.cursor()

        try:
            cur.execute(
                """
                SELECT
                    SUBSTR(last_payment_date_raw, 1, 7) AS period,
                    COUNT(*) AS identity_count,
                    COALESCE(SUM(lifetime_net_received), 0) AS total_revenue,
                    COALESCE(AVG(financial_value_score), 0) AS avg_financial_value_score
                FROM financial_identity_profile
                WHERE last_payment_date_raw IS NOT NULL
                  AND LENGTH(last_payment_date_raw) >= 7
                GROUP BY SUBSTR(last_payment_date_raw, 1, 7)
                ORDER BY period DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cur.fetchall()
        except sqlite3.OperationalError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Trend query unavailable: {e}",
            )

        data = [dict(r) for r in rows]

        return {
            "count": len(data),
            "limit": limit,
            "data": data,
        }
    finally:
        conn.close()


'''

marker = r'(?=@router\.get\("/scheduling/priority"\))'

if re.search(r'@router\.get\("/dashboard/trends"\)', text):
    raise SystemExit("dashboard/trends already exists.")

new_text, count = re.subn(marker, insert_block, text, count=1)
if count != 1:
    raise SystemExit(f"Insertion failed. Matched markers: {count}")

path.write_text(new_text, encoding="utf-8")
print("Inserted /dashboard/trends successfully.")
