import sqlite3

DB = "atieh_clinic.db"

def get_engine_scoring_config(conn) -> dict:
    rows = conn.execute("SELECT key, value FROM engine_scoring_config").fetchall()
    kv = {k: v for (k, v) in rows}

    def f(key: str, default: float) -> float:
        try:
            return float(kv.get(key, default))
        except Exception:
            return float(default)

    return {
        "FIN_MAX_BOOST": f("FIN_MAX_BOOST", 12.0),
        "FIN_MAX_BOOST_IF_URGENT": f("FIN_MAX_BOOST_IF_URGENT", 3.0),
    }

def get_financial_value_score_by_record_no(conn, record_no: str) -> float:
    row = conn.execute(
        "SELECT financial_value_score FROM v_financial_for_engine_recordno WHERE record_no = ?",
        (str(record_no).strip(),)
    ).fetchone()

    if not row or row[0] is None:
        return 0.0

    try:
        s = float(row[0])
    except Exception:
        return 0.0

    return max(0.0, min(1.0, s))

def compute_priority(base_score: float, fin_score: float, is_urgent: bool, cfg: dict) -> dict:
    max_boost = cfg["FIN_MAX_BOOST_IF_URGENT"] if is_urgent else cfg["FIN_MAX_BOOST"]
    fin_boost = max_boost * fin_score
    return {
        "base_score": base_score,
        "financial_value_score": fin_score,
        "financial_max_boost_used": max_boost,
        "financial_boost": fin_boost,
        "ai_priority_score": base_score + fin_boost,
    }

def main():
    con = sqlite3.connect(DB)
    cfg = get_engine_scoring_config(con)

    # تست: بالاترین‌ها
    top = con.execute("""
        SELECT record_no, financial_value_score
        FROM v_financial_for_engine_recordno
        ORDER BY financial_value_score DESC
        LIMIT 3
    """).fetchall()

    # تست: یکی با صفر
    zero = con.execute("""
        SELECT record_no, financial_value_score
        FROM v_financial_for_engine_recordno
        WHERE financial_value_score = 0
        LIMIT 1
    """).fetchone()

    print("CONFIG:", cfg)
    print("\nTOP3:")
    for rn, _ in top:
        fin = get_financial_value_score_by_record_no(con, rn)
        print("record_no:", rn, compute_priority(base_score=50.0, fin_score=fin, is_urgent=False, cfg=cfg))

    if zero:
        rn0 = zero[0]
        fin0 = get_financial_value_score_by_record_no(con, rn0)
        print("\nZERO:")
        print("record_no:", rn0, compute_priority(base_score=50.0, fin_score=fin0, is_urgent=False, cfg=cfg))
        print("\nZERO (URGENT):")
        print("record_no:", rn0, compute_priority(base_score=50.0, fin_score=fin0, is_urgent=True, cfg=cfg))

    con.close()

if __name__ == "__main__":
    main()