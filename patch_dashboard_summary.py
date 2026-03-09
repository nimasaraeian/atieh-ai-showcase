from pathlib import Path
import re

path = Path(r".\app\api\financial_operational.py")
text = path.read_text(encoding="utf-8")

pattern = r'''@router\.get\("/dashboard/summary"\)\s*
def get_dashboard_summary\(\):.*?
(?=\n# .*Scheduling priority)'''

replacement = '''@router.get("/dashboard/summary")
def get_dashboard_summary():
    """
    Return executive summary counts for the operational dashboard.

    Includes:
    - operational queue counts
    - scheduling priority band counts
    - financial identity counts
    - revenue totals
    - financial tier distribution
    """
    conn = get_financial_db()
    try:
        cur = conn.cursor()
        result = {}

        # Operational counts from views
        for view, key in [
            ("v_financial_followup_queue_contactable", "total_followup_contactable"),
            ("v_financial_followup_daily_balanced", "total_daily_balanced"),
            ("v_financial_scheduling_queue_top300", "total_scheduling_top300"),
        ]:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {view}")
                result[key] = cur.fetchone()[0]
            except sqlite3.OperationalError:
                result[key] = 0

        # Priority band counts from top300
        for band, key in [
            ("CRITICAL_PRIORITY", "critical_priority_count"),
            ("HIGH_PRIORITY", "high_priority_count"),
            ("MEDIUM_PRIORITY", "medium_priority_count"),
        ]:
            try:
                cur.execute(
                    """
                    SELECT COUNT(*) FROM v_financial_scheduling_queue_top300
                    WHERE scheduling_band = ?
                    """,
                    (band,),
                )
                result[key] = cur.fetchone()[0]
            except sqlite3.OperationalError:
                result[key] = 0

        # Financial identity overview
        try:
            cur.execute("SELECT COUNT(*) FROM financial_identity_profile")
            result["total_financial_identities"] = cur.fetchone()[0]
        except sqlite3.OperationalError:
            result["total_financial_identities"] = 0

        try:
            cur.execute(
                """
                SELECT COALESCE(SUM(lifetime_net_received), 0)
                FROM financial_identity_profile
                """
            )
            result["total_revenue"] = cur.fetchone()[0]
        except sqlite3.OperationalError:
            result["total_revenue"] = 0

        # Tier distribution
        for tier, key in [
            ("VIP", "vip_count"),
            ("HIGH", "high_count"),
            ("MEDIUM", "medium_count"),
            ("LOW", "low_count"),
        ]:
            try:
                cur.execute(
                    """
                    SELECT COUNT(*) FROM financial_identity_profile
                    WHERE financial_tier = ?
                    """,
                    (tier,),
                )
                result[key] = cur.fetchone()[0]
            except sqlite3.OperationalError:
                result[key] = 0

        # Simple readiness flags
        result["has_financial_identity_engine"] = result["total_financial_identities"] > 0
        result["followup_queue_ready"] = result["total_followup_contactable"] > 0
        result["scheduling_queue_ready"] = result["total_scheduling_top300"] > 0
        result["has_vip_segment"] = result["vip_count"] > 0

        return result
    finally:
        conn.close()


'''

new_text, count = re.subn(pattern, replacement, text, flags=re.DOTALL)
if count != 1:
    raise SystemExit(f"Replacement failed. Matched blocks: {count}")

path.write_text(new_text, encoding="utf-8")
print("Patched get_dashboard_summary successfully.")
