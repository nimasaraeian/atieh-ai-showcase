import sqlite3
import os

DB_PATH = os.getenv("ATIEH_DB_PATH", "atieh_clinic_recovery81_test.db")


def table_columns(conn, table_name):
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]


def build_insert(conn, table_name, row_dict):
    cols = table_columns(conn, table_name)
    use_cols = [c for c in row_dict.keys() if c in cols]
    placeholders = ",".join(["?"] * len(use_cols))
    sql = f"INSERT INTO {table_name} ({','.join(use_cols)}) VALUES ({placeholders})"
    vals = [row_dict[c] for c in use_cols]
    return sql, vals


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    promoted_table = "identity_expansion_promoted_phase3"
    candidate_table = "identity_expansion_candidates_phase3"

    print("Promoted columns:", ", ".join(table_columns(conn, promoted_table)))
    print("Candidate columns:", ", ".join(table_columns(conn, candidate_table)))

    conn.execute(f"DELETE FROM {promoted_table}")

    rows = conn.execute(f'''
        SELECT
            source_type,
            source_row_id,
            target_patient_id,
            COALESCE(expansion_rule, 'P6_unknown') AS expansion_rule,
            COALESCE(support_signal_count, 0) AS support_signal_count,
            COALESCE(score_raw, 0) AS score_raw,
            COALESCE(confidence_level, 'REJECT') AS confidence_level
        FROM {candidate_table}
    ''').fetchall()

    grouped = {}
    for row in rows:
        key = (row["source_type"], row["source_row_id"])
        grouped.setdefault(key, []).append(row)

    promoted_count = 0
    ambiguous_count = 0

    for (src_type, src_id), candidates in grouped.items():
        elig = [c for c in candidates if c["confidence_level"] in ("EXP_A", "EXP_B")]
        if not elig:
            continue

        elig = sorted(elig, key=lambda x: float(x["score_raw"]), reverse=True)

        best = elig[0]
        second = elig[1] if len(elig) > 1 else None

        dominance_margin = None
        if second is not None:
            dominance_margin = float(best["score_raw"]) - float(second["score_raw"])
            if dominance_margin < 15:
                ambiguous_count += 1
                continue

        row_dict = {
            "source_type": src_type,
            "source_row_id": src_id,
            "target_patient_id": best["target_patient_id"],
            "expansion_rule": best["expansion_rule"],
            "support_signal_count": best["support_signal_count"],
            "score": best["score_raw"],
            "score_raw": best["score_raw"],
            "confidence_level": best["confidence_level"],
            "dominance_margin": dominance_margin,
            "promotion_reason": "dominant_score_from_precomputed_score_raw",
            "match_status": "promoted",
        }

        sql, vals = build_insert(conn, promoted_table, row_dict)
        conn.execute(sql, vals)
        promoted_count += 1

    conn.commit()
    print("Phase3 promoted:", promoted_count)
    print("Phase3 ambiguous skipped:", ambiguous_count)
    conn.close()


if __name__ == "__main__":
    main()
