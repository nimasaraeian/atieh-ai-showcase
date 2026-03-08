import sqlite3
import re

DB_PATH = "atieh_clinic.db"
RECNO_RE = re.compile(r"\((\d+)\)\s*$")

def norm_phone(s: str | None) -> str | None:
    if not s:
        return None
    digits = "".join(ch for ch in str(s) if ch.isdigit())
    if not digits:
        return None

    # common Iran formats
    if digits.startswith("0098"):
        digits = digits[2:]  # -> 98...
    if digits.startswith("98") and len(digits) >= 12:
        digits = "0" + digits[2:]
    if len(digits) == 10 and digits.startswith("9"):
        digits = "0" + digits

    # if people pasted multiple numbers, keep the LAST 11 digits if plausible
    if len(digits) > 11:
        digits = digits[-11:]

    if len(digits) < 10:
        return None
    return digits

def norm_name(s: str | None) -> str:
    s = (s or "").strip()
    s = s.replace("ي", "ی").replace("ك", "ک").replace("\u200c", " ")
    s = " ".join(s.split())
    return s

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # patients stats
    p_total = cur.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
    p_phone = cur.execute("SELECT COUNT(*) FROM patients WHERE phone IS NOT NULL AND TRIM(phone)<>''").fetchone()[0]

    print("\n--- patients stats ---")
    print("patients total:", p_total)
    print("patients with phone:", p_phone)

    # build patient phone_norm set
    p_phone_norm = set()
    for (ph,) in cur.execute("SELECT phone FROM patients WHERE phone IS NOT NULL AND TRIM(phone)<>''"):
        n = norm_phone(ph)
        if n:
            p_phone_norm.add(n)

    print("patients phone_norm unique:", len(p_phone_norm))

    # stg stats
    s_total = cur.execute("SELECT COUNT(*) FROM stg_payments").fetchone()[0]
    s_has_phone = cur.execute("SELECT COUNT(*) FROM stg_payments WHERE phone_raw IS NOT NULL AND TRIM(phone_raw)<>''").fetchone()[0]
    print("\n--- stg_payments stats ---")
    print("stg total:", s_total)
    print("stg has phone_raw:", s_has_phone)

    # sample normalize rate + overlap
    # (برای سرعت، نمونه‌گیری می‌کنیم)
    sample = 200000
    rows = cur.execute(
        "SELECT phone_raw FROM stg_payments WHERE phone_raw IS NOT NULL AND TRIM(phone_raw)<>'' LIMIT ?",
        (sample,)
    ).fetchall()

    s_norm = 0
    overlap = 0
    bad_examples = []
    for (ph,) in rows:
        n = norm_phone(ph)
        if n:
            s_norm += 1
            if n in p_phone_norm:
                overlap += 1
            elif len(bad_examples) < 25:
                bad_examples.append((ph, n))

    print("\n--- phone normalization diagnostics (sample) ---")
    print("sample size:", len(rows))
    print("normalized ok:", s_norm)
    print("overlap with patients phone_norm:", overlap)
    if s_norm:
        print("overlap rate among normalized:", round(overlap / s_norm, 4))

    print("\n--- examples: phone_raw -> phone_norm that DO NOT exist in patients ---")
    for raw, n in bad_examples:
        print(raw, "=>", n)

    # record_no extraction sanity
    rec_ok = 0
    rec_bad = 0
    for (name_raw,) in cur.execute("SELECT patient_name_raw FROM stg_payments LIMIT 2000").fetchall():
        s = norm_name(name_raw)
        if RECNO_RE.search(s):
            rec_ok += 1
        else:
            rec_bad += 1
    print("\n--- record_no extraction sanity (2000 rows) ---")
    print("ok:", rec_ok, "bad:", rec_bad)

    conn.close()

if __name__ == "__main__":
    main()