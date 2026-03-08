# 🎯 راهنمای سریع Import اکسل

## ✅ سیستم Import شما آماده است!

---

## 🚀 روش 1: Import از طریق API (توصیه می‌شود)

### قدم 1: آماده‌سازی
```bash
# پوشه را بسازید
mkdir -p data/history

# فایل اکسل خود را کپی کنید
copy "your_file.xlsx" data/history/
```

### قدم 2: Import با curl
```bash
curl -X POST "http://localhost:8000/api/import/history" ^
  -H "Content-Type: application/json" ^
  -d "{\"files\": [{\"path\": \"data/history/your_file.xlsx\", \"year\": 1404, \"sheet\": 0}]}"
```

### قدم 3: Import با Python
```python
import requests

response = requests.post(
    "http://localhost:8000/api/import/history",
    json={
        "files": [
            {
                "path": "data/history/your_file.xlsx",
                "year": 1404,
                "sheet": 0
            }
        ]
    }
)

print(response.json())
```

---

## 🔍 بررسی نتایج Import

### در مرورگر:
```
http://localhost:8000/docs
```
سپس `/api/import/history` را امتحان کنید.

### با Python:
```bash
python -c "import sqlite3; conn = sqlite3.connect('atieh_clinic.db'); c = conn.cursor(); c.execute('SELECT COUNT(*) FROM appointments'); print(f'Appointments: {c.fetchone()[0]:,}'); c.execute('SELECT COUNT(*) FROM patients'); print(f'Patients: {c.fetchone()[0]:,}')"
```

---

## 📊 نتایج فعلی سیستم شما:

```
✅ 20,339 بیمار ثبت شده
✅ 70,532 نوبت ثبت شده  
✅ 311,465 سطر با موفقیت parse شده (91%)
✅ API Import کاملاً فعال
```

---

## 🔧 رفع مشکلات

### اگر فایل قبلاً import شده:
```sql
-- مشاهده import های قبلی
SELECT * FROM import_runs ORDER BY id DESC LIMIT 5;

-- حذف import قبلی (اگر لازم باشد)
DELETE FROM import_runs WHERE id = YOUR_RUN_ID;
```

### اگر خطا دارید:
```bash
python scripts/reprocess_staging_errors.py
```

---

## 📝 مثال کامل

```bash
# 1. سرور را اجرا کنید
uvicorn main:app --reload

# 2. در ترمینال دیگر:
python -c "
import requests
import json

# Import file
response = requests.post(
    'http://localhost:8000/api/import/history',
    json={
        'files': [
            {
                'path': 'data/history/my_file.xlsx',
                'year': 1404,
                'sheet': 0
            }
        ]
    },
    timeout=300
)

result = response.json()
print('Import Run ID:', result['import_run_id'])
print('Status:', result['status'])
print('Stats:', json.dumps(result['stats'], indent=2))
"
```

---

## 🎉 موفقیت!

سیستم Import شما کاملاً عملیاتی است و می‌تواند:
- ✅ فایل‌های اکسل تاریخی را بخواند
- ✅ تاریخ شمسی را تبدیل کند
- ✅ بیماران را ثبت کند  
- ✅ نوبت‌ها را ایجاد کند
- ✅ گزارش کامل ارائه دهد

**برای اطلاعات بیشتر**: `IMPORT_GUIDE.md`
