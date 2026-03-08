import sqlite3
from typing import Dict


# ---------------------------
# Config Loader
# ---------------------------

def get_engine_scoring_config(conn: sqlite3.Connection) -> Dict[str, float]:
    rows = conn.execute(
        "SELECT key, value FROM engine_scoring_config"
    ).fetchall()

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


# ---------------------------
# Financial Score Fetcher (RecordNo-native)
# ---------------------------

def get_financial_value_score(
    conn: sqlite3.Connection,
    record_no: str
) -> float:

    row = conn.execute(
        """
        SELECT financial_value_score
        FROM v_financial_for_engine_recordno
        WHERE record_no = ?
        """,
        (str(record_no).strip(),)
    ).fetchone()

    if not row or row[0] is None:
        return 0.0

    try:
        score = float(row[0])
    except Exception:
        return 0.0

    # Clamp to 0..1
    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0

    return score


# ---------------------------
# Financial Boost Injector
# ---------------------------

def apply_financial_boost(
    conn: sqlite3.Connection,
    base_score: float,
    record_no: str,
    is_urgent: bool
) -> Dict:

    cfg = get_engine_scoring_config(conn)

    fin_score = get_financial_value_score(conn, record_no)

    max_boost = (
        cfg["FIN_MAX_BOOST_IF_URGENT"]
        if is_urgent
        else cfg["FIN_MAX_BOOST"]
    )

    financial_boost = max_boost * fin_score

    final_score = base_score + financial_boost

    return {
        "record_no": record_no,
        "ai_priority_score_base": base_score,
        "financial_value_score": fin_score,
        "financial_max_boost_used": max_boost,
        "financial_boost": financial_boost,
        "ai_priority_score": final_score,
    }