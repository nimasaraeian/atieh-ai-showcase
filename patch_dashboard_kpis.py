from pathlib import Path
import re

path = Path(r".\app\api\financial_operational.py")
text = path.read_text(encoding="utf-8")

insert_block = r'''
@router.get("/dashboard/kpis")
def get_dashboard_kpis():
    """
    Return compact KPI cards for dashboard usage.
    """
    conn = get_financial_db()
    try:
        cur = conn.cursor()

        # Financial totals
        try:
            cur.execute("SELECT COUNT(*) FROM financial_identity_profile")
            total_financial_identities = cur.fetchone()[0]
        except sqlite3.OperationalError:
            total_financial_identities = 0

        try:
            cur.execute(
                "SELECT COALESCE(SUM(lifetime_net_received), 0) FROM financial_identity_profile"
            )
            total_revenue = cur.fetchone()[0] or 0
        except sqlite3.OperationalError:
            total_revenue = 0

        # Tier counts
        tier_counts = {}
        for tier in ["VIP", "HIGH", "MEDIUM", "LOW"]:
            try:
                cur.execute(
                    "SELECT COUNT(*) FROM financial_identity_profile WHERE financial_tier = ?",
                    (tier,),
                )
                tier_counts[tier] = cur.fetchone()[0]
            except sqlite3.OperationalError:
                tier_counts[tier] = 0

        vip_count = tier_counts["VIP"]
        high_count = tier_counts["HIGH"]

        # Follow-up queue
        try:
            cur.execute("SELECT COUNT(*) FROM v_financial_followup_queue_contactable")
            total_followup_contactable = cur.fetchone()[0]
        except sqlite3.OperationalError:
            total_followup_contactable = 0

        try:
            cur.execute("SELECT COUNT(*) FROM v_financial_followup_daily_balanced")
            total_daily_balanced = cur.fetchone()[0]
        except sqlite3.OperationalError:
            total_daily_balanced = 0

        # Scheduling queue
        try:
            cur.execute("SELECT COUNT(*) FROM v_financial_scheduling_queue_top300")
            total_scheduling_top300 = cur.fetchone()[0]
        except sqlite3.OperationalError:
            total_scheduling_top300 = 0

        try:
            cur.execute(
                """
                SELECT COUNT(*) FROM v_financial_scheduling_queue_top300
                WHERE scheduling_band = 'CRITICAL_PRIORITY'
                """
            )
            critical_priority_count = cur.fetchone()[0]
        except sqlite3.OperationalError:
            critical_priority_count = 0

        avg_revenue_per_identity = (
            total_revenue / total_financial_identities if total_financial_identities > 0 else 0
        )

        followup_backlog_days = (
            total_followup_contactable / total_daily_balanced if total_daily_balanced > 0 else None
        )

        return {
            "total_revenue": total_revenue,
            "total_financial_identities": total_financial_identities,
            "avg_revenue_per_identity": round(avg_revenue_per_identity, 2),
            "vip_count": vip_count,
            "vip_plus_high_count": vip_count + high_count,
            "total_followup_contactable": total_followup_contactable,
            "followup_backlog_days": round(followup_backlog_days, 2) if followup_backlog_days is not None else None,
            "total_scheduling_top300": total_scheduling_top300,
            "critical_priority_count": critical_priority_count,
        }
    finally:
        conn.close()


'''

marker = r'(?=@router\.get\("/scheduling/priority"\))'

if re.search(r'@router\.get\("/dashboard/kpis"\)', text):
    raise SystemExit("dashboard/kpis already exists.")

new_text, count = re.subn(marker, insert_block, text, count=1)
if count != 1:
    raise SystemExit(f"Insertion failed. Matched markers: {count}")

path.write_text(new_text, encoding="utf-8")
print("Inserted /dashboard/kpis successfully.")
