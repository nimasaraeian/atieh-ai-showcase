import sqlite3
import re
from collections import Counter

DB_PATH = r"C:\Users\USER\Documents\GitHub\atieh\atieh_clinic_recovery81_test.db"

pattern = re.compile(r"\b\d{10}\b")

def is_valid_national_id(code: str) -> bool:
    if not code or len(code) != 10 or not code.isdigit():
        return False

    # reject repeated digits like 0000000000 / 1111111111 / ...
    if len(set(code)) == 1:
        return False

    check = int(code[-1])
    s = sum(int(code[i]) * (10 - i) for i in range(9))
    r = s % 11

    if r < 2:
        return check == r
    return check == (11 - r)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("SELECT id, row_json FROM stg_payments")

total_rows = 0
rows_with_any_10 = 0
rows_with_nonmobile_10 = 0
rows_with_valid_nid = 0

all_10_count = 0
nonmobile_10_count = 0
valid_nid_count = 0

samples_valid = []
samples_mixed = []

for row_id, row_json in cur:
    total_rows += 1
    text = row_json or ""
    nums = pattern.findall(text)

    if nums:
        rows_with_any_10 += 1
        all_10_count += len(nums)

    nonmobile = [x for x in nums if not x.startswith("9")]
    if nonmobile:
        rows_with_nonmobile_10 += 1
        nonmobile_10_count += len(nonmobile)

    valid_nids = [x for x in nonmobile if is_valid_national_id(x)]
    if valid_nids:
        rows_with_valid_nid += 1
        valid_nid_count += len(valid_nids)

        if len(samples_valid) < 30:
            samples_valid.append((row_id, valid_nids))

    if nums and valid_nids and len(samples_mixed) < 30:
        samples_mixed.append((row_id, nums, valid_nids))

    if total_rows % 50000 == 0:
        print(f"scanned: {total_rows}")

conn.close()

print("\n=== SUMMARY ===")
print("TOTAL_ROWS:", total_rows)
print("ROWS_WITH_ANY_10_DIGIT:", rows_with_any_10)
print("ROWS_WITH_NONMOBILE_10_DIGIT:", rows_with_nonmobile_10)
print("ROWS_WITH_VALID_NATIONAL_ID:", rows_with_valid_nid)
print("TOTAL_10_DIGIT_VALUES:", all_10_count)
print("TOTAL_NONMOBILE_10_DIGIT_VALUES:", nonmobile_10_count)
print("TOTAL_VALID_NATIONAL_ID_VALUES:", valid_nid_count)

print("\n=== SAMPLE VALID NATIONAL IDS ===")
for item in samples_valid:
    print(item)

print("\n=== SAMPLE MIXED ROWS (all nums vs valid nid) ===")
for item in samples_mixed:
    print(item)