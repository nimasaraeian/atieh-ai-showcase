# ATIEH AI — Bridge Pipeline Runbook

## Purpose

This document records the full operational workflow used to build the historical bridge pipeline between:

- `payments_clean` source files
- historical appointment files
- patient identity / `record_no`

The goal of this bridge layer is to connect payment rows to real patient appointment history across multiple years, so that later layers such as:

- patient lifetime value
- patient financial score
- retention analysis
- AI scheduling priority
- VIP patient detection

can be built on top of a reliable identity linkage foundation.

---

# Project Base Path

```powershell
C:\Users\USER\Documents\GitHub\atieh
Main Database
atieh_clinic.db
Main Inputs
Payments

Located in:

data\inputs\payments\

Examples:

payments_1404_full.xlsx

payments_1403_full.xlsx

payments_1402_full.xlsx

payments_1400_full.xlsx

payments_1399_full.xlsx

payments_1398_full.xlsx

payments_1396_full.xlsx

payments_1395_full.xlsx

Appointment History

Located in:

data\inputs\history\<YEAR>\

Examples:

data\inputs\history\1403\نوبت_دهی_بیمارانی_که_حضور_پیدا_کردند_1403.xlsx

data\inputs\history\1402\نوبت_دهی_بیمارانی_که_حضور_پیدا_میکنند_1402.xlsx

data\inputs\history\1400\...

data\inputs\history\1399\...

data\inputs\history\1398\...

data\inputs\history\1396\...

data\inputs\history\1395\...

Bridge Pipeline Goal

For each year, build:

bridge_<YEAR>_payment_appointment

bridge_<YEAR>_review

patient_recordno_map_<YEAR>

The matching logic is based on:

Tier A → date + name + phone

Tier B → date + name unique

Tier C → name + phone

Core Script Pattern

For each year, a dedicated script is used:

scripts\bridge_<YEAR>_payment_appointment.py

Examples:

scripts\bridge_1403_payment_appointment.py

scripts\bridge_1402_payment_appointment.py

scripts\bridge_1400_payment_appointment.py

scripts\bridge_1399_payment_appointment.py

scripts\bridge_1398_payment_appointment.py

scripts\bridge_1396_payment_appointment.py

scripts\bridge_1395_payment_appointment.py

Important Technical Lessons Learned
1) Appointment headers may contain single quotes

Example:

'تاريخ نوبت'
'نام بيمار(تشكيل پرونده شده)'
'تلفن'

Therefore header cleaning is required.

2) Persian/Arabic character normalization is required

Particularly:

ي → ی

ك → ک

3) Phone parsing must support multiple numbers

Examples:

1;09144407540

09033493070;09120193137

4) Direct hard-pin of the appointment file is preferred

Fallback works, but hard-pin is cleaner and more reliable.

5) Some years may have low CRM coverage

Example:

year 1396 had only 111 appointment rows in CRM, so the pipeline result is technically correct but low-coverage.

Standard Workflow For Adding A New Year
Step 1 — Find payment file
Get-ChildItem . -Recurse -File | Where-Object {
    $_.Name -match "<YEAR>" -and $_.Name -match "payment|payments|پرداخت|دریافت|مالی|صورتحساب|receipt"
} | Select-Object FullName, Name, Length, LastWriteTime | Format-Table -AutoSize
Step 2 — Find appointment file
Get-ChildItem . -Recurse -File | Where-Object {
    $_.Name -match "<YEAR>" -and $_.Name -match "نوبت|appointment|visit|مراجعه|turn|وقت"
} | Select-Object FullName, Name, Length, LastWriteTime | Format-Table -AutoSize
Step 3 — Find all candidate files for the year
Get-ChildItem . -Recurse -File -Include *.xlsx,*.xls,*.csv | Where-Object {
    $_.Name -match "<YEAR>"
} | Select-Object FullName, Name, Length, LastWriteTime | Sort-Object Name | Format-Table -AutoSize
Step 4 — Copy the previous year's script

Example: copying 1403 to 1402

Copy-Item ".\scripts\bridge_1403_payment_appointment.py" ".\scripts\bridge_1402_payment_appointment.py" -Force

General form:

Copy-Item ".\scripts\bridge_<PREV_YEAR>_payment_appointment.py" ".\scripts\bridge_<YEAR>_payment_appointment.py" -Force
Step 5 — Replace previous year with new year

Example:

(Get-Content ".\scripts\bridge_1402_payment_appointment.py" -Raw) `
-replace '1403','1402' `
| Set-Content ".\scripts\bridge_1402_payment_appointment.py" -Encoding UTF8

General form:

(Get-Content ".\scripts\bridge_<YEAR>_payment_appointment.py" -Raw) `
-replace '<PREV_YEAR>','<YEAR>' `
| Set-Content ".\scripts\bridge_<YEAR>_payment_appointment.py" -Encoding UTF8
Step 6 — Inspect exact appointment filename inside the year's history folder

Example:

Get-ChildItem ".\data\inputs\history\1402" -File | Select-Object Name, FullName | Format-Table -AutoSize

General form:

Get-ChildItem ".\data\inputs\history\<YEAR>" -File | Select-Object Name, FullName | Format-Table -AutoSize
Step 7 — Hard-pin the real appointment filename
Example for year 1402
(Get-Content ".\scripts\bridge_1402_payment_appointment.py" -Raw) `
-replace 'REAL_FILE_NAME\.xlsx','نوبت_دهی_بیمارانی_که_حضور_پیدا_میکنند_1402.xlsx' `
| Set-Content ".\scripts\bridge_1402_payment_appointment.py" -Encoding UTF8
General pattern
(Get-Content ".\scripts\bridge_<YEAR>_payment_appointment.py" -Raw) `
-replace 'REAL_FILE_NAME\.xlsx','<EXACT_APPOINTMENT_FILENAME>.xlsx' `
| Set-Content ".\scripts\bridge_<YEAR>_payment_appointment.py" -Encoding UTF8

If the old script still contains a previous year's exact filename, replace that too:

(Get-Content ".\scripts\bridge_<YEAR>_payment_appointment.py" -Raw) `
-replace '<OLD_EXACT_FILENAME>\.xlsx','<NEW_EXACT_FILENAME>.xlsx' `
| Set-Content ".\scripts\bridge_<YEAR>_payment_appointment.py" -Encoding UTF8
Step 8 — Verify final paths inside the script

Example:

Select-String -Path ".\scripts\bridge_1402_payment_appointment.py" -Pattern "payments_1402_full|history|1402|REAL_FILE_NAME|EXACT_|نوبت_دهی"

General form:

Select-String -Path ".\scripts\bridge_<YEAR>_payment_appointment.py" -Pattern "payments_<YEAR>_full|history|<YEAR>|REAL_FILE_NAME|EXACT_|نوبت_دهی"
Step 9 — Run the bridge pipeline

Example:

python .\scripts\bridge_1402_payment_appointment.py

General form:

python .\scripts\bridge_<YEAR>_payment_appointment.py
Step 10 — QA checks after execution
Count bridge rows
sqlite3 .\atieh_clinic.db "SELECT COUNT(*) FROM bridge_<YEAR>_payment_appointment;"
Count patient map rows
sqlite3 .\atieh_clinic.db "SELECT COUNT(*) FROM patient_recordno_map_<YEAR>;"
Count review reasons
sqlite3 .\atieh_clinic.db "SELECT review_reason, COUNT(*) FROM bridge_<YEAR>_review GROUP BY review_reason;"
Count match methods
sqlite3 .\atieh_clinic.db "SELECT match_method, COUNT(*) FROM bridge_<YEAR>_payment_appointment GROUP BY match_method;"
Header / Mapping Debug Workflow

If a year returns zero matches or suspiciously low matches, use the following checks.

Check available files in the year's history folder
Get-ChildItem ".\data\inputs\history\<YEAR>" -File | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize
Check path-related lines inside the script
Select-String -Path ".\scripts\bridge_<YEAR>_payment_appointment.py" -Pattern "appt_path|appt_dir|glob\(" -CaseSensitive:$false | Sort-Object LineNumber | Select-Object LineNumber, Line | Format-Table -AutoSize
View script lines
$lines = Get-Content ".\scripts\bridge_<YEAR>_payment_appointment.py"
1..260 | ForEach-Object { "{0,4}: {1}" -f $_, $lines[$_-1] }

If needed:

261..520 | ForEach-Object { "{0,4}: {1}" -f $_, $lines[$_-1] }
Appointment File Inspection
Inspect actual shape and columns

Example:

python -c "import pandas as pd; p=r'.\data\inputs\history\1396\نوبت_دهی_بیمارانی_که_حضور_پیدا_میکنند_1396.xlsx'; df=pd.read_excel(p, sheet_name=0); print(df.shape); print(list(df.columns))"

General form:

python -c "import pandas as pd; p=r'.\data\inputs\history\<YEAR>\<APPOINTMENT_FILE>.xlsx'; df=pd.read_excel(p, sheet_name=0); print(df.shape); print(list(df.columns))"
Debug Script Used During Investigation

A temporary debug script was used to inspect appointment files and payments schema.

Script content
import pandas as pd
import sqlite3
from pathlib import Path

repo = Path(r"C:\Users\USER\Documents\GitHub\atieh")
db_path = repo / "atieh_clinic.db"
appt_path = repo / "data" / "inputs" / "history" / "1403" / "نوبت_دهی_بیمارانی_که_حضور_پیدا_کردند_1403.xlsx"

print("=" * 80)
print("APPOINTMENT FILE CHECK")
print("=" * 80)

xls = pd.ExcelFile(appt_path)
print("Sheets:", xls.sheet_names)

for s in xls.sheet_names:
    print(f"\n--- SHEET: {s} ---")
    df = pd.read_excel(appt_path, sheet_name=s)
    print("Shape:", df.shape)
    print("Columns:")
    for c in df.columns:
        print(" -", repr(c))
    print("\nHead:")
    print(df.head(5).to_string())

print("\n" + "=" * 80)
print("PAYMENTS TABLE CHECK")
print("=" * 80)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("\nPayments schema:")
schema = cur.execute("PRAGMA table_info(payments_clean)").fetchall()
for row in schema:
    print(row)

print("\nSample payment rows:")
rows = cur.execute("SELECT * FROM payments_clean LIMIT 5").fetchall()
for r in rows:
    print(r)

conn.close()
Important Fix Applied To Header Constants

The header candidate block inside the bridge script was repaired to avoid corrupted encoding and to use clean Persian labels.

Final correct header constants
# Column candidates
PAYMENT_DATE_HEADERS = ["تاریخ پذیرش", "تاريخ پذيرش", "تاریخ", "تاريخ"]
PAYMENT_NAME_HEADERS = ["نام بیمار", "نام بيمار", "نام بیمار(تشکیل پرونده شده)"]
PAYMENT_PHONE_HEADERS = ["موبایل", "موبايل", "تلفن", "شماره تماس"]
PAYMENT_RECORDNO_HEADERS = ["شماره پرونده", "کد پرونده", "record_no", "پرونده"]

APPT_DATE_HEADERS = ["تاریخ نوبت", "تاريخ نوبت", "تاریخ", "تاريخ"]
APPT_NAME_HEADERS = [
    "نام بیمار(تشکیل پرونده شده)",
    "نام بيمار(تشكيل پرونده شده)",
    "نام و نام خانوادگی",
    "نام بیمار",
    "نام بيمار",
]
APPT_PHONE_HEADERS = ["موبایل", "موبايل", "تلفن", "شماره تماس", "تلفن همراه"]
Main Matching Logic Summary
Tier A

Exact match on:

date

normalized name

overlapping normalized phone

Tier B

Exact match on:

date

normalized name

And only accepted when unique on both sides.

Tier C

Exact match on:

normalized name

overlapping normalized phone

Used when date is missing / weak.

Years Completed
Strong / usable years

1404

1403

1402

1400

1399

1398

Partial / low-coverage year

1396
Note: CRM itself had only 111 appointment rows, so the low match count is expected and technically correct.

Missing / unavailable year

1397
Not available.

Skipped due to missing payment

1401
Payment file not available.

Final remaining historical year handled

1395

Operational Results Summary
1403

accepted: 34507

patient map: 11835

A: 31809

B: 1708

C: 990

1402

accepted: 30042

patient map: 11200

A: 27160

B: 1939

C: 943

1400

accepted: 16406

patient map: 6952

A: 12572

B: 3004

C: 830

1399

accepted: 12335

patient map: 5813

A: 9531

B: 2211

C: 593

1398

accepted: 5190

patient map: 2943

A: 4373

B: 441

C: 376

1396

accepted: 104

patient map: 98

A: 93

B: 3

C: 8

Notes About PowerShell

All PowerShell commands in this document are intended to be copy-paste ready and were used directly inside:

PS C:\Users\USER\Documents\GitHub\atieh>
Recommended Next Phase

After historical bridge completion, the next layer should be:

patient_recordno_map_all

patient_financial_value

patient_lifetime_value

financial segmentation

AI scheduling priority

This bridge layer is the foundation for the Atieh AI Financial Intelligence Layer.