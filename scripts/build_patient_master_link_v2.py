# -*- coding: utf-8 -*-
"""
Build patient_master_link_v2: link payment_identity_master to patients_identity_normalized.

Deterministic linking priority:
  Tier A: national_id exact; OR (crm_code/record_no exact + patient_name_key exact); OR (crm_code/record_no exact + phone exact)
  Tier B: crm_code exact + exact name; crm_code exact + exact national_id; crm_code exact + exact phone
  Tier C: exact name + exact phone; exact name + exact national_id
  Tier D: name only / phone only / similarity only => review_flag=1

For each crm_patient_code we assign at most one patient_id (best tier). If multiple candidates at same tier, review_flag=1.
Does NOT modify source tables.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

TIER_ORDER = {"A": 4, "B": 3, "C": 2, "D": 1}


def _patient_phones_set(phone_all_norm_json: str | None) -> set[str]:
    if not phone_all_norm_json:
        return set()
    try:
        arr = json.loads(phone_all_norm_json)
        return {x for x in arr if x and isinstance(x, str)}
    except Exception:
        return set()


def run_schema(conn: sqlite3.Connection) -> None:
    path = REPO / "sql" / "identity_resolution" / "014_payment_identity_master_v2_schema.sql"
    if path.exists():
        conn.executescript(path.read_text(encoding="utf-8"))
    conn.commit()


def main() -> None:
    db_path = REPO / "atieh_clinic_recovery81_test.db"
    if not db_path.exists():
        print(f"DB not found: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    run_schema(conn)

    conn.execute("DELETE FROM patient_master_link_v2")
    conn.commit()

    # Load payment identity master
    payment_master = {}
    for row in conn.execute("""
        SELECT crm_patient_code, canonical_record_no, canonical_patient_name, patient_name_key,
               canonical_national_id_norm, primary_phone_norm, all_phones_json
        FROM payment_identity_master
    """).fetchall():
        payment_master[row[0]] = {
            "canonical_record_no": row[1],
            "canonical_patient_name": row[2],
            "patient_name_key": (row[3] or "").strip() or None,
            "canonical_national_id_norm": (row[4] or "").strip() or None,
            "primary_phone_norm": (row[5] or "").strip() or None,
            "all_phones_json": row[6],
        }

    # Load patients: list of (patient_id, patient_name_key, phone_primary_norm, phone_all_norm_json, national_id_norm)
    patients = conn.execute("""
        SELECT patient_id, patient_name_key, phone_primary_norm, phone_all_norm_json, national_id_norm
        FROM patients_identity_normalized
    """).fetchall()

    # Index patients by national_id, name_key, primary_phone for fast lookup
    by_nid: dict[str, list[int]] = defaultdict(list)
    by_name_key: dict[str, list[int]] = defaultdict(list)
    by_phone: dict[str, list[int]] = defaultdict(list)
    patient_map: dict[int, tuple] = {}
    for p in patients:
        pid, name_key, phone_primary, phone_all_json, nid = p
        patient_map[pid] = (name_key, phone_primary, phone_all_json, nid)
        if nid and (nid or "").strip():
            by_nid[(nid or "").strip()].append(pid)
        if name_key and (name_key or "").strip():
            by_name_key[(name_key or "").strip()].append(pid)
        if phone_primary and (phone_primary or "").strip():
            by_phone[(phone_primary or "").strip()].append(pid)
        for ph in _patient_phones_set(phone_all_json):
            if ph:
                by_phone[ph].append(pid)

    ins = """
        INSERT INTO patient_master_link_v2 (crm_patient_code, patient_id, link_tier, link_rule, confidence_score, review_flag, review_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    tier_a_count = tier_b_count = tier_c_count = tier_d_count = review_count = 0

    for crm_code, pay in payment_master.items():
        # For each patient, record the best (tier, rule, score) they qualify for
        patient_best: dict[int, tuple[str, str, float]] = {}  # patient_id -> (tier, rule, score)

        nid_pay = pay.get("canonical_national_id_norm")
        name_key_pay = pay.get("patient_name_key")
        phone_pay = pay.get("primary_phone_norm")
        has_crm_or_record = bool(crm_code or pay.get("canonical_record_no"))

        def set_if_better(pid: int, tier: str, rule: str, score: float) -> None:
            if pid not in patient_best or TIER_ORDER.get(tier, 0) > TIER_ORDER.get(patient_best[pid][0], 0):
                patient_best[pid] = (tier, rule, score)

        # Tier A: national_id exact
        if nid_pay:
            for pid in by_nid.get(nid_pay, []):
                set_if_better(pid, "A", "national_id_exact", 1.0)

        # Tier A: crm_code/record_no + name_key exact
        if has_crm_or_record and name_key_pay:
            for pid in by_name_key.get(name_key_pay, []):
                set_if_better(pid, "A", "crm_record_plus_name_key", 1.0)

        # Tier A: crm_code/record_no + phone exact
        if has_crm_or_record and phone_pay:
            for pid in by_phone.get(phone_pay, []):
                set_if_better(pid, "A", "crm_record_plus_phone", 1.0)

        # Tier B: crm_code + name exact
        if name_key_pay:
            for pid in by_name_key.get(name_key_pay, []):
                set_if_better(pid, "B", "crm_plus_name", 0.9)

        # Tier B: crm_code + national_id exact
        if nid_pay:
            for pid in by_nid.get(nid_pay, []):
                set_if_better(pid, "B", "crm_plus_national_id", 0.9)

        # Tier B: crm_code + phone exact
        if phone_pay:
            for pid in by_phone.get(phone_pay, []):
                set_if_better(pid, "B", "crm_plus_phone", 0.9)

        # Tier C: name exact + phone exact
        if name_key_pay and phone_pay:
            for pid in set(by_name_key.get(name_key_pay, [])) & set(by_phone.get(phone_pay, [])):
                set_if_better(pid, "C", "name_plus_phone", 0.8)

        # Tier C: name exact + national_id exact
        if name_key_pay and nid_pay:
            for pid in set(by_name_key.get(name_key_pay, [])) & set(by_nid.get(nid_pay, [])):
                set_if_better(pid, "C", "name_plus_national_id", 0.8)

        # Tier D: name only or phone only (only if no better tier yet)
        if name_key_pay:
            for pid in by_name_key.get(name_key_pay, []):
                set_if_better(pid, "D", "name_only", 0.5)
        if phone_pay:
            for pid in by_phone.get(phone_pay, []):
                set_if_better(pid, "D", "phone_only", 0.5)

        if not patient_best:
            continue

        # Best tier among all candidates (A > B > C > D)
        best_tier = max((t for _, (t, _, _) in patient_best.items()), key=lambda t: TIER_ORDER.get(t, 0))
        best_candidates = [(pid, patient_best[pid][1], patient_best[pid][2]) for pid, (t, _, _) in patient_best.items() if t == best_tier]
        best_rule = best_candidates[0][1]
        best_score = best_candidates[0][2]
        review_flag = 1 if len(best_candidates) > 1 or best_tier == "D" else 0
        review_reason = None
        if len(best_candidates) > 1:
            review_reason = "multiple_candidates_same_tier"
        elif best_tier == "D":
            review_reason = "tier_d_review"

        chosen_patient_id = min(c[0] for c in best_candidates)
        conn.execute(ins, (crm_code, chosen_patient_id, best_tier, best_rule, best_score, review_flag, review_reason))

        if best_tier == "A":
            tier_a_count += 1
        elif best_tier == "B":
            tier_b_count += 1
        elif best_tier == "C":
            tier_c_count += 1
        else:
            tier_d_count += 1
        if review_flag:
            review_count += 1

    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM patient_master_link_v2").fetchone()[0]
    print(f"Built patient_master_link_v2: {total:,} links")
    print(f"  Tier A: {tier_a_count:,}  Tier B: {tier_b_count:,}  Tier C: {tier_c_count:,}  Tier D: {tier_d_count:,}")
    print(f"  Review flag set: {review_count:,}")
    conn.close()


if __name__ == "__main__":
    main()
