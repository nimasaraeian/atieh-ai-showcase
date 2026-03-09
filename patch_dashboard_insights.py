from pathlib import Path
import re

path = Path(r".\app\api\financial_operational.py")
text = path.read_text(encoding="utf-8")

insert_block = r'''
@router.get("/dashboard/insights")
def get_dashboard_insights():
    """
    Return management-level insights derived from dashboard summary metrics.
    """
    conn = get_financial_db()
    try:
        cur = conn.cursor()
        result = {}

        # Base metrics
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

        vip_count = tier_counts["VIP"]
        high_count = tier_counts["HIGH"]

        avg_revenue_per_identity = (
            total_revenue / total_financial_identities if total_financial_identities > 0 else 0
        )

        vip_share_pct = (
            (vip_count / total_financial_identities) * 100 if total_financial_identities > 0 else 0
        )

        high_plus_vip_share_pct = (
            ((vip_count + high_count) / total_financial_identities) * 100
            if total_financial_identities > 0 else 0
        )

        followup_backlog_days = (
            total_followup_contactable / total_daily_balanced if total_daily_balanced > 0 else None
        )

        result["system_status"] = (
            "ready"
            if total_financial_identities > 0 and total_scheduling_top300 > 0
            else "partial"
        )

        result["financial_engine_status"] = (
            "active" if total_financial_identities > 0 and total_revenue > 0 else "inactive"
        )

        result["vip_segment_status"] = (
            "present_but_small"
            if vip_count > 0 and vip_share_pct < 1
            else "present"
            if vip_count > 0
            else "missing"
        )

        result["followup_backlog_status"] = (
            "high"
            if followup_backlog_days is not None and followup_backlog_days > 30
            else "moderate"
            if followup_backlog_days is not None and followup_backlog_days > 7
            else "low"
        )

        result["scheduling_pressure_status"] = (
            "critical"
            if critical_priority_count >= 20
            else "elevated"
            if critical_priority_count > 0
            else "normal"
        )

        result["priority_queue_status"] = (
            "fully_populated" if total_scheduling_top300 >= 300 else "underfilled"
        )

        result["insights"] = [
            f"Financial engine contains {total_financial_identities} identities with total tracked revenue of {total_revenue}.",
            f"VIP segment size is {vip_count}, while VIP+HIGH combined represents {high_plus_vip_share_pct:.2f}% of all financial identities.",
            f"Contactable follow-up queue contains {total_followup_contactable} patients.",
            f"At the current daily balanced rate ({total_daily_balanced}/day), the follow-up backlog is approximately {followup_backlog_days:.1f} days."
            if followup_backlog_days is not None
            else "Daily follow-up capacity is not available.",
            f"Scheduling queue currently holds {total_scheduling_top300} patients, including {critical_priority_count} in CRITICAL_PRIORITY."
        ]

        result["metrics"] = {
            "total_financial_identities": total_financial_identities,
            "total_revenue": total_revenue,
            "avg_revenue_per_identity": avg_revenue_per_identity,
            "vip_share_pct": round(vip_share_pct, 4),
            "high_plus_vip_share_pct": round(high_plus_vip_share_pct, 4),
            "followup_backlog_days": round(followup_backlog_days, 2) if followup_backlog_days is not None else None,
            "critical_priority_count": critical_priority_count,
            "tier_counts": tier_counts,
        }

        return result
    finally:
        conn.close()


'''

marker = r'(?=@router\.get\("/scheduling/priority"\))'

if re.search(r'@router\.get\("/dashboard/insights"\)', text):
    raise SystemExit("dashboard/insights already exists.")

new_text, count = re.subn(marker, insert_block, text, count=1)
if count != 1:
    raise SystemExit(f"Insertion failed. Matched markers: {count}")

path.write_text(new_text, encoding="utf-8")
print("Inserted /dashboard/insights successfully.")
