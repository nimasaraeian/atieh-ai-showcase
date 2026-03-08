import sqlite3
import math

DB_PATH = "atieh_clinic.db"

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

def safe_log1p(x: float) -> float:
    return math.log1p(max(0.0, x))

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # rebuild from scratch (idempotent)
    cur.execute("DELETE FROM patient_financial_summary")
    conn.commit()

    rows = cur.execute("""
        SELECT
          record_no,
          COUNT(*) AS txn_count,
          SUM(COALESCE(net_received, 0)) AS net_sum,
          SUM(COALESCE(amount_patient, 0)) AS patient_sum,
          SUM(COALESCE(amount_insurer, 0)) AS insurer_sum,

          SUM(CASE WHEN COALESCE(net_received,0) < 0 THEN COALESCE(net_received,0) ELSE 0 END) AS neg_net_sum,
          SUM(CASE WHEN COALESCE(net_received,0) < 0 THEN 1 ELSE 0 END) AS neg_txn_count,

          MIN(appointment_date_raw) AS first_date_raw,
          MAX(appointment_date_raw) AS last_date_raw,

          SUM(CASE WHEN payer_source_norm='cash' THEN 1 ELSE 0 END) AS cash_cnt,
          SUM(CASE WHEN payer_source_norm='insurance' THEN 1 ELSE 0 END) AS ins_cnt,

          SUM(CASE WHEN loaded_at >= datetime('now','-30 day') THEN 1 ELSE 0 END) AS recent_cnt,
          SUM(CASE WHEN loaded_at >= datetime('now','-30 day') THEN COALESCE(net_received,0) ELSE 0 END) AS recent_net
        FROM payments_clean
        WHERE record_no IS NOT NULL AND TRIM(record_no) <> ''
        GROUP BY record_no
    """).fetchall()

    print("aggregated record_no rows:", len(rows))

    net_values = [r[2] or 0 for r in rows]
    txn_values = [r[1] or 0 for r in rows]
    recent_values = [r[12] or 0 for r in rows]

    max_net = max([safe_log1p(v) for v in net_values] + [1.0])
    max_txn = max(txn_values + [1])
    max_recent = max([safe_log1p(v) for v in recent_values] + [1.0])

    inserted = 0
    for r in rows:
        (record_no, txn_count, net_sum, patient_sum, insurer_sum,
         neg_net_sum, neg_txn_count,
         first_date_raw, last_date_raw,
         cash_cnt, ins_cnt,
         recent_cnt, recent_net) = r

        monetary = clamp01(safe_log1p(net_sum) / max_net)
        frequency = clamp01((txn_count / max_txn) if max_txn else 0.0)
        recent_m = clamp01(safe_log1p(recent_net) / max_recent)

        neg_penalty = 0.0
        if txn_count and neg_txn_count:
            neg_rate = neg_txn_count / txn_count
            neg_penalty = min(0.5, neg_rate)

        mix_boost = 0.0
        if txn_count:
            cash_rate = (cash_cnt / txn_count) if cash_cnt else 0.0
            mix_boost = 0.1 * cash_rate

        score = (0.55 * monetary) + (0.25 * frequency) + (0.20 * recent_m) + mix_boost - neg_penalty
        score = clamp01(score)

        cur.execute("""
            INSERT INTO patient_financial_summary (
              record_no,
              lifetime_txn_count, lifetime_net_received, lifetime_patient_paid, lifetime_insurer_paid,
              lifetime_negative_net, lifetime_negative_txn_count,
              first_payment_date_raw, last_payment_date_raw,
              cash_txn_count, insurance_txn_count,
              recent_txn_count, recent_net_received,
              financial_value_score,
              updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))
        """, (
            record_no,
            int(txn_count or 0), float(net_sum or 0), float(patient_sum or 0), float(insurer_sum or 0),
            float(neg_net_sum or 0), int(neg_txn_count or 0),
            first_date_raw, last_date_raw,
            int(cash_cnt or 0), int(ins_cnt or 0),
            int(recent_cnt or 0), float(recent_net or 0),
            float(score)
        ))
        inserted += 1

    conn.commit()
    print("inserted summaries:", inserted)

    top = cur.execute("""
        SELECT record_no, lifetime_net_received, lifetime_txn_count, financial_value_score
        FROM patient_financial_summary
        ORDER BY financial_value_score DESC
        LIMIT 10
    """).fetchall()

    print("\nTOP 10 by financial_value_score:")
    for row in top:
        print(row)

    conn.close()

if __name__ == "__main__":
    main()