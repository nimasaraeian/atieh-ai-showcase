import sqlite3
import ast
import re
from collections import Counter, defaultdict

DB_PATH = r"C:\Users\USER\Documents\GitHub\atieh\atieh_clinic_recovery81_test.db"

def norm_text(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    s = s.replace("ي", "ی").replace("ك", "ک")
    s = s.replace("\u200c", "").replace("\u200f", "").replace("\ufeff", "")
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    return s

def norm_key(s: str) -> str:
    s = norm_text(s)
    s = s.replace("'", "").replace('"', "")
    s = s.replace("‌", "")
    s = s.replace(" ", "")
    return s

def extract_digits(s: str) -> str:
    if s is None:
        return ""
    return "".join(ch for ch in str(s) if ch.isdigit())

def is_valid_national_id_10(d: str) -> bool:
    return len(d) == 10

def safe_parse_row_json(txt: str):
    if not txt:
        return None
    try:
        return ast.literal_eval(txt)
    except Exception:
        return None

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM stg_payments")
    total_rows = cur.fetchone()[0]

    print(f"TOTAL_ROWS = {total_rows}")

    cur.execute("SELECT id, file_name, import_run_id, row_number, row_json FROM stg_payments")

    key_counter = Counter()
    national_key_rows = 0
    national_nonempty_rows = 0
    national_valid_10_rows = 0
    parse_failures = 0

    national_samples = []
    file_counter_for_national = Counter()
    raw_key_variants = Counter()

    checked = 0

    for row_id, file_name, import_run_id, row_number, row_json in cur:
        checked += 1
        obj = safe_parse_row_json(row_json)
        if not isinstance(obj, dict):
            parse_failures += 1
            continue

        found_national_key_in_this_row = False

        for k, v in obj.items():
            nk = norm_key(k)
            key_counter[nk] += 1
            raw_key_variants[str(k)] += 1

            if nk in {"کدملی", "كدملی", "کدملي", "كدملي"}:
                found_national_key_in_this_row = True
                national_key_rows += 1
                file_counter_for_national[file_name] += 1

                val = norm_text(v)
                digits = extract_digits(val)

                if val != "":
                    national_nonempty_rows += 1

                if is_valid_national_id_10(digits):
                    national_valid_10_rows += 1
                    if len(national_samples) < 50:
                        national_samples.append({
                            "id": row_id,
                            "file_name": file_name,
                            "import_run_id": import_run_id,
                            "row_number": row_number,
                            "raw_key": str(k),
                            "raw_value": str(v),
                            "digits": digits,
                        })

        if checked % 50000 == 0:
            print(f"SCANNED = {checked}")

    conn.close()

    print("\n=== SUMMARY ===")
    print(f"TOTAL_ROWS                = {total_rows}")
    print(f"PARSE_FAILURES            = {parse_failures}")
    print(f"ROWS_WITH_NATIONAL_KEY    = {national_key_rows}")
    print(f"ROWS_WITH_NONEMPTY_VALUE  = {national_nonempty_rows}")
    print(f"ROWS_WITH_VALID_10_DIGIT  = {national_valid_10_rows}")

    print("\n=== TOP NORMALIZED KEYS ===")
    for k, c in key_counter.most_common(50):
        print(f"{k}\t{c}")

    print("\n=== RAW KEY VARIANTS MATCHING NATIONAL ID ===")
    for k, c in raw_key_variants.most_common():
        nk = norm_key(k)
        if nk in {"کدملی", "كدملی", "کدملي", "كدملي"}:
            print(f"{k}\t{c}")

    print("\n=== FILES CONTAINING NATIONAL ID KEY ===")
    for fname, c in file_counter_for_national.most_common(50):
        print(f"{fname}\t{c}")

    print("\n=== SAMPLE VALID NATIONAL IDs ===")
    for s in national_samples:
        print(s)

if __name__ == "__main__":
    main()