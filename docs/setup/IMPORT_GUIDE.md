# 📥 راهنمای Import فایل‌های اکسل تاریخی

## 🎯 قابلیت‌ها

سیستم می‌تواند فایل‌های اکسل تاریخی را import کند:
- ✅ تبدیل خودکار تاریخ شمسی به میلادی
- ✅ استخراج اطلاعات بیماران
- ✅ ثبت نوبت‌ها
- ✅ مدیریت خطاها
- ✅ گزارش کامل

---

## 📁 گام 1: آماده‌سازی فایل

فایل اکسل خود را در یکی از این پوشه‌ها قرار دهید:

```
atieh/
├── data/
│   └── history/           ← اینجا
│       └── your_file.xlsx
├── data/inputs/history/
│   └── 1404/              ← یا اینجا
│       └── your_file.xlsx
└── uploads/               ← یا اینجا
    └── your_file.xlsx
```

---

## ⚡ گام 2: Import (3 روش)

### روش 1: اسکریپت خودکار (ساده‌ترین) ⭐

```bash
python scripts/test_import_excel.py
```

این اسکریپت:
- ✅ خودکار فایل‌ها را پیدا می‌کند
- ✅ Import را انجام می‌دهد
- ✅ نتیجه را نمایش می‌دهد

---

### روش 2: API با curl/Postman

**Start Server:**
```bash
uvicorn main:app --reload
```

**Import via API:**
```bash
curl -X POST "http://localhost:8000/api/import/history" \
  -H "Content-Type: application/json" \
  -d '{
    "files": [
      {
        "path": "data/history/your_file.xlsx",
        "year": 1404,
        "sheet": 0
      }
    ]
  }'
```

---

### روش 3: مستقیم با Python

```python
from app.importers.history_importer import import_history_excel
from database import get_db

db = next(get_db())

result = import_history_excel(
    file_path="data/history/your_file.xlsx",
    db=db,
    year_hint=1404,
    import_run_id=1
)

print(f"Imported: {result['appointments_created']} appointments")
print(f"Patients: {result['patients_created']} patients")
```

---

## 📊 گام 3: بررسی نتایج

### در مرورگر:
```
http://localhost:8000/api/import/history?limit=10
```

### با اسکریپت:
```bash
python scripts/show_top_errors.py
```

### مستقیم از دیتابیس:
```bash
python -c "
import sqlite3
conn = sqlite3.connect('atieh_clinic.db')
c = conn.cursor()

# تعداد کل
c.execute('SELECT COUNT(*) FROM stg_appointments')
print(f'Total rows: {c.fetchone()[0]:,}')

# وضعیت parse
c.execute('SELECT parse_status, COUNT(*) FROM stg_appointments GROUP BY parse_status')
for row in c.fetchall():
    print(f'{row[0]}: {row[1]:,}')

conn.close()
"
```

---

## 🔍 گام 4: رفع خطاها (در صورت نیاز)

اگر خطا داشتید، اجرا کنید:

```bash
python scripts/reprocess_staging_errors.py
```

---

## 📋 مثال کامل

```bash
# 1. فایل را کپی کنید
mkdir -p data/history
cp "نوبت_دهی_1404.xlsx" data/history/

# 2. سرور را اجرا کنید
uvicorn main:app --reload

# 3. Import کنید (ترمینال دیگر)
python scripts/test_import_excel.py

# 4. نتایج را ببینید
python -c "
import sqlite3
conn = sqlite3.connect('atieh_clinic.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM appointments')
print(f'Total appointments: {c.fetchone()[0]:,}')
c.execute('SELECT COUNT(*) FROM patients')
print(f'Total patients: {c.fetchone()[0]:,}')
conn.close()
"
```

---

## ⚠️ نکات مهم

1. **فرمت فایل**: فایل باید `.xlsx` یا `.xls` باشد
2. **ستون‌ها**: باید شامل ستون‌های استاندارد باشد:
   - نام بیمار
   - تلفن
   - تاریخ نوبت
   - نام پزشک
   - سازمان بیمه‌گر
   - توضیحات
3. **تاریخ شمسی**: سیستم خودکار تبدیل می‌کند
4. **خطاها**: نگران نباشید! سیستم خطاها را log می‌کند و بعداً قابل رفع است

---

## 🎉 نتیجه مورد انتظار

```
✅ Import completed!
   - Total rows: 342,894
   - Successful: 311,465 (91%)
   - Errors: 31,421 (9% - mostly empty dates)
   - Appointments created: 70,532
   - Patients created: 20,339
```

---

## 📞 رفع مشکل

### خطا: "Server is not running"
```bash
uvicorn main:app --reload
```

### خطا: "File not found"
- مسیر فایل را بررسی کنید
- از مسیر نسبی استفاده کنید: `data/history/file.xlsx`

### خطا: "Permission denied"
```bash
chmod +r data/history/your_file.xlsx  # Linux/Mac
```

### Import خیلی کند است
- نگران نباشید! Import فایل‌های بزرگ زمان می‌برد
- حدود 100-200 سطر در ثانیه

---

## 🚀 Import Bulk (چند فایل همزمان)

```bash
curl -X POST "http://localhost:8000/api/import/history" \
  -H "Content-Type: application/json" \
  -d '{
    "files": [
      {"path": "data/history/file1.xlsx", "year": 1403, "sheet": 0},
      {"path": "data/history/file2.xlsx", "year": 1404, "sheet": 0},
      {"path": "data/history/file3.xlsx", "year": 1404, "sheet": 1}
    ]
  }'
```
