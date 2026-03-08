from fastapi import APIRouter, Query, HTTPException
import sqlite3

router = APIRouter(prefix="/ai/financial", tags=["AI Financial (RecordNo)"])

DB_PATH = "atieh_clinic.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def tier_and_action(financial_value_score: float):
    """
    Tier calibration based on real distribution in your dataset:
      VIP    >= 0.85
      HIGH   >= 0.70
      MEDIUM >= 0.50
      LOW    <  0.50
    """
    s = float(financial_value_score or 0.0)
    if s >= 0.85:
        return "VIP", "تماس فوری + نوبت نزدیک + پیشنهاد خدمات تکمیلی"
    if s >= 0.70:
        return "HIGH", "اولویت بالا برای نوبت‌دهی"
    if s >= 0.50:
        return "MEDIUM", "نوبت‌دهی معمولی (مناسب پر کردن اسلات‌ها)"
    return "LOW", "اولویت پایین / فقط در اسلات‌های خالی"


def fetch_by_score_range(
    conn,
    min_lifetime: float,
    score_min: float,
    score_max_exclusive: float | None,
    limit: int,
):
    if limit <= 0:
        return []

    if score_max_exclusive is None:
        sql = """
        SELECT
          record_no, financial_value_score,
          lifetime_net_received, lifetime_txn_count,
          recent_net_received, recent_txn_count,
          last_payment_date_raw
        FROM v_financial_for_engine_recordno
        WHERE COALESCE(lifetime_net_received,0) >= ?
          AND financial_value_score >= ?
        ORDER BY financial_value_score DESC, lifetime_net_received DESC
        LIMIT ?
        """
        params = (min_lifetime, score_min, limit)
    else:
        sql = """
        SELECT
          record_no, financial_value_score,
          lifetime_net_received, lifetime_txn_count,
          recent_net_received, recent_txn_count,
          last_payment_date_raw
        FROM v_financial_for_engine_recordno
        WHERE COALESCE(lifetime_net_received,0) >= ?
          AND financial_value_score >= ?
          AND financial_value_score < ?
        ORDER BY financial_value_score DESC, lifetime_net_received DESC
        LIMIT ?
        """
        params = (min_lifetime, score_min, score_max_exclusive, limit)

    rows = conn.execute(sql, params).fetchall()
    items = []
    for r in rows:
        d = dict(r)
        s = float(d.get("financial_value_score") or 0.0)
        tier, action = tier_and_action(s)
        d["tier"] = tier
        d["action_hint"] = action
        items.append(d)
    return items


# ── fill_shortage helpers ─────────────────────────────────────────────────────

TIERS_ORDER = ["VIP", "HIGH", "MEDIUM", "LOW"]
TIER_INDEX = {t: i for i, t in enumerate(TIERS_ORDER)}


def _take_unique(items: list, k: int, selected: set) -> list:
    out = []
    for it in items:
        rn = it.get("record_no")
        if rn and rn not in selected:
            out.append(it)
            selected.add(rn)
            if len(out) >= k:
                break
    return out


def _donor_tiers_for(target_tier: str) -> list:
    idx = TIER_INDEX[target_tier]
    return TIERS_ORDER[:idx]


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.get("/top-recordnos")
def top_recordnos(
    limit: int = Query(20, ge=1, le=200),
    min_lifetime: float = Query(1.0),
):
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT
              record_no,
              financial_value_score,
              lifetime_net_received,
              lifetime_txn_count,
              recent_net_received,
              recent_txn_count,
              last_payment_date_raw
            FROM v_financial_for_engine_recordno
            WHERE COALESCE(lifetime_net_received, 0) >= ?
            ORDER BY financial_value_score DESC, lifetime_net_received DESC
            LIMIT ?
            """,
            (min_lifetime, limit),
        ).fetchall()

        return {
            "limit": limit,
            "min_lifetime": min_lifetime,
            "count": len(rows),
            "items": [dict(r) for r in rows],
        }
    finally:
        conn.close()


@router.get("/top-recordnos-explain-mixed")
def top_recordnos_explain_mixed(
    vip: int = Query(3, ge=0, le=200),
    high: int = Query(3, ge=0, le=200),
    medium: int = Query(2, ge=0, le=200),
    low: int = Query(2, ge=0, le=200),
    min_lifetime: float = Query(1.0),
    fill_shortage: bool = Query(False),
):
    conn = get_db()
    try:
        requested = {"VIP": vip, "HIGH": high, "MEDIUM": medium, "LOW": low}
        requested_total = sum(requested.values())

        POOL_CAP = 500
        pools = {
            "VIP":    fetch_by_score_range(conn, min_lifetime, 0.85, None,  POOL_CAP),
            "HIGH":   fetch_by_score_range(conn, min_lifetime, 0.70, 0.85,  POOL_CAP),
            "MEDIUM": fetch_by_score_range(conn, min_lifetime, 0.50, 0.70,  POOL_CAP),
            "LOW":    fetch_by_score_range(conn, min_lifetime, 0.00, 0.50,  POOL_CAP),
        }

        available_total = len({
            it["record_no"]
            for tier_items in pools.values()
            for it in tier_items
            if it.get("record_no")
        })

        selected: set = set()

        picked_by_tier: dict = {}
        for tier in TIERS_ORDER:
            picked_by_tier[tier] = _take_unique(pools[tier], requested[tier], selected)

        returned_by_tier = {t: len(picked_by_tier[t]) for t in TIERS_ORDER}
        missing_by_tier = {
            t: max(0, requested[t] - returned_by_tier[t]) for t in TIERS_ORDER
        }

        filled = {"VIP": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "TOTAL": 0}
        filled_by_source = {"VIP": {}, "HIGH": {}, "MEDIUM": {}, "LOW": {}}

        if fill_shortage:
            for target in TIERS_ORDER:
                shortage = missing_by_tier[target]
                if shortage <= 0:
                    continue

                donors = list(reversed(_donor_tiers_for(target)))
                for donor in donors:
                    if shortage <= 0:
                        break
                    taken = _take_unique(pools.get(donor, []), shortage, selected)
                    if taken:
                        picked_by_tier[target].extend(taken)
                        filled[target] += len(taken)
                        filled["TOTAL"] += len(taken)
                        filled_by_source[target][donor] = (
                            filled_by_source[target].get(donor, 0) + len(taken)
                        )
                        shortage -= len(taken)

            # recompute for all tiers after the full fill pass
            returned_by_tier = {t: len(picked_by_tier[t]) for t in TIERS_ORDER}
            missing_by_tier = {
                t: max(0, requested[t] - returned_by_tier[t]) for t in TIERS_ORDER
            }

        fill_shortage_satisfied = sum(missing_by_tier.values()) == 0

        items = []
        for t in TIERS_ORDER:
            for it in picked_by_tier[t]:
                items.append({**it, "tier": t})

        resp = {
            "min_lifetime": min_lifetime,
            "requested": requested,
            "requested_total": requested_total,
            "available_total": available_total,
            "returned_by_tier": returned_by_tier,
            "missing_by_tier": missing_by_tier,
            "fill_shortage": fill_shortage,
            "fill_shortage_satisfied": fill_shortage_satisfied,
            "count": len(items),
            "items": items,
        }

        if fill_shortage:
            resp["filled"] = filled
            resp["filled_by_source"] = filled_by_source

        return resp
    finally:
        conn.close()


@router.get("/top-recordnos-explain")
def top_recordnos_explain(
    limit: int = Query(20, ge=1, le=200),
    min_lifetime: float = Query(1.0),
):
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT
              record_no,
              financial_value_score,
              lifetime_net_received,
              lifetime_txn_count,
              recent_net_received,
              recent_txn_count,
              last_payment_date_raw
            FROM v_financial_for_engine_recordno
            WHERE COALESCE(lifetime_net_received, 0) >= ?
            ORDER BY financial_value_score DESC, lifetime_net_received DESC
            LIMIT ?
            """,
            (min_lifetime, limit),
        ).fetchall()

        items = []
        for r in rows:
            d = dict(r)
            tier, action = tier_and_action(d.get("financial_value_score"))
            d["tier"] = tier
            d["action_hint"] = action
            items.append(d)

        return {
            "limit": limit,
            "min_lifetime": min_lifetime,
            "count": len(items),
            "items": items,
        }
    finally:
        conn.close()


@router.get("/recordno/{record_no}")
def financial_by_recordno(record_no: str):
    conn = get_db()
    try:
        row = conn.execute(
            """
            SELECT
              record_no,
              financial_value_score,
              lifetime_net_received,
              lifetime_txn_count,
              recent_net_received,
              recent_txn_count,
              last_payment_date_raw
            FROM v_financial_for_engine_recordno
            WHERE record_no = ?
            """,
            (record_no,),
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="record_no not found")

        return dict(row)
    finally:
        conn.close()


@router.get("/status")
def financial_status(sample_limit: int = Query(5, ge=1, le=50)):
    conn = get_db()
    try:
        total = conn.execute(
            "SELECT COUNT(*) AS c FROM v_financial_for_engine_recordno"
        ).fetchone()["c"]

        zero_lifetime = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM v_financial_for_engine_recordno
            WHERE COALESCE(lifetime_net_received, 0) = 0
            """
        ).fetchone()["c"]

        score_minmax = conn.execute(
            """
            SELECT
              MIN(financial_value_score) AS min_score,
              MAX(financial_value_score) AS max_score
            FROM v_financial_for_engine_recordno
            """
        ).fetchone()

        date_minmax = conn.execute(
            """
            SELECT
              MIN(last_payment_date_raw) AS min_date,
              MAX(last_payment_date_raw) AS max_date
            FROM v_financial_for_engine_recordno
            """
        ).fetchone()

        sample = conn.execute(
            f"""
            SELECT
              record_no,
              financial_value_score,
              lifetime_net_received,
              lifetime_txn_count,
              recent_net_received,
              recent_txn_count,
              last_payment_date_raw
            FROM v_financial_for_engine_recordno
            ORDER BY financial_value_score DESC, lifetime_net_received DESC
            LIMIT {int(sample_limit)}
            """
        ).fetchall()

        tiers = conn.execute(
            """
            SELECT
              CASE
                WHEN financial_value_score >= 0.85 THEN 'VIP'
                WHEN financial_value_score >= 0.70 THEN 'HIGH'
                WHEN financial_value_score >= 0.50 THEN 'MEDIUM'
                ELSE 'LOW'
              END AS tier,
              COUNT(*) AS cnt
            FROM v_financial_for_engine_recordno
            GROUP BY 1
            ORDER BY cnt DESC
            """
        ).fetchall()

        return {
            "db_path": DB_PATH,
            "view": "v_financial_for_engine_recordno",
            "total_rows": int(total),
            "zero_lifetime_net_received": int(zero_lifetime),
            "zero_lifetime_pct": round((zero_lifetime / max(total, 1)) * 100.0, 2),
            "score_min": float(score_minmax["min_score"] or 0.0),
            "score_max": float(score_minmax["max_score"] or 0.0),
            "last_payment_date_min": date_minmax["min_date"],
            "last_payment_date_max": date_minmax["max_date"],
            "tier_distribution": [dict(r) for r in tiers],
            "top_sample": [dict(r) for r in sample],
        }
    finally:
        conn.close()
