# Production-Grade Slot Recommendations - Summary

تاریخ: 2026-02-06
هدف: تبدیل `/ai/recommend-slot` به یک endpoint production-ready با doctor assignment، confidence scoring، و ranking واقعی

---

## ✅ تغییرات انجام شده

### A) Doctor Assignment (حل مشکل "AUTO")

**مشکل قبلی:**
- تمام slot‌ها `doctor_id="AUTO"` و `doctor_name=null` برمی‌گشتند

**راه‌حل:**
- ✅ ساخت `app/engine/slot_recommender.py` با:
  - کلاس `SlotWithDoctor` برای نگهداری اطلاعات کامل slot
  - کلاس `ProductionSlotRecommender` برای تولید slot‌ها با doctor assignment
  - تابع `recommend_slots_with_doctors()` به عنوان interface اصلی

**نتیجه:**
- هر slot حالا شامل `doctor_id` (مثل "D006") و `doctor_name` (مثل "دکتر رضایی") می‌باشد
- Doctor assignment بر اساس schedules واقعی از `data/mock/schedules.json` انجام می‌شود

---

### B) Confidence Scoring (0-1 Range)

**مشکل قبلی:**
- تمام slot‌ها `confidence=1.0` داشتند (هیچ variance‌ای وجود نداشت)

**راه‌حل:**
- ✅ پیاده‌سازی سیستم confidence scoring با فاکتورهای زیر:
  ```
  base = 0.55
  + 0.15 اگر slot در 3 روز آینده باشد
  + 0.10 اگر صبح باشد و urgency بالا
  + 0.10 اگر با priority بیمار همخوانی داشته باشد
  - 0.15 اگر دکتر آن روز load بالایی داشته باشد
  - 0.10 اگر slot نزدیک به یک block باشد
  + 0.05 اگر دکتر rating بالا (>=4.8) داشته باشد
  ```

**نتیجه:**
- Confidence حالا بین 0.0 تا 1.0 متغیر است
- مثال: `[0.90, 0.85, 0.75]` به جای `[1.0, 1.0, 1.0]`

---

### C) Ranking & Diversity

**مشکل قبلی:**
- Slot‌ها فقط به ترتیب زمانی بودند (همه صبح یک روز)

**راه‌حل:**
- ✅ پیاده‌سازی الگوریتم ranking و diversity:
  1. تولید 60 candidate slot
  2. محاسبه confidence برای هر کدام
  3. مرتب‌سازی بر اساس confidence
  4. اعمال قوانین diversity:
     - حداکثر 2 slot پشت سر هم
     - حداکثر 2 slot از یک دکتر
     - توزیع در روزهای مختلف (برای `days_ahead > 7`)

**نتیجه:**
- Slot‌ها متنوع‌تر و پخش‌تر در زمان
- دکترهای مختلف در نتایج
- کاهش تمرکز در یک بازه زمانی خاص

---

### D) Value Score (Non-Zero)

**مشکل قبلی:**
- `value_score` همیشه 0 بود

**راه‌حل:**
- ✅ تغییر در `ai_brain.py`:
  - تبدیل `value_score` از `float (0-1)` به `int (0-100)`
  - محاسبه واقعی بر اساس:
    - نوع پرداخت (+25 برای نقدی)
    - lifetime (>24 ماه: +20، >12 ماه: +15، >6 ماه: +10)
    - تعداد نوبت‌های قبلی (>10: +10، >5: +5)
    - نرخ تکمیل (>0.9: +10، >0.7: +5)
    - عدم حضور (>3: -15، >1: -10)
    - پرداخت دیر (>3: -15، >1: -10)

**نتیجه:**
- `value_score` حالا بین 20 تا 100 است (معمولاً 40-90)
- مثال: `value_score: 80` برای یک بیمار خوب

---

### E) Persian Encoding (UTF-8)

**بررسی انجام شده:**
- ✅ تایید شد که تمام JSON loadها با `encoding='utf-8'` هستند
- ✅ هیچ `.encode()` یا `.decode()` غیرضروری وجود ندارد
- ✅ متن فارسی به صورت plain Python `str` ذخیره می‌شود
- ✅ API به درستی UTF-8 را در Content-Type header برمی‌گرداند

**نتیجه:**
- متون فارسی در JSON به درستی encode شده‌اند
- مشکل نمایش در PowerShell فقط یک مسئله console display است (نه JSON encoding)

---

## 📄 فایل‌های ایجاد/تغییر شده

### فایل‌های جدید:
1. **`app/engine/slot_recommender.py`** (457 خط)
   - کلاس‌های `SlotWithDoctor` و `ProductionSlotRecommender`
   - منطق کامل تولید slot، confidence scoring، و diversity

2. **`tests/test_recommend_slot_has_real_doctor.py`**
   - تست doctor assignment
   - تست تنوع دکترها

3. **`tests/test_confidence_range_and_variance.py`**
   - تست محدوده confidence (0-1)
   - تست تنوع confidence values
   - تست مرتب‌سازی

4. **`tests/test_value_score_nonzero.py`**
   - تست non-zero بودن value_score
   - تست محدوده (0-100)
   - تست تنوع بین بیماران

5. **`tests/test_persian_encoding_ok.py`**
   - تست encoding صحیح متون فارسی
   - تست عدم وجود mojibake
   - تست عدم double encoding

### فایل‌های تغییر یافته:
1. **`ai_brain.py`**
   - تغییر `value_score` از float (0-1) به int (0-100)

2. **`main.py`**
   - افزودن import `Any`
   - افزودن `get_crm_client_dependency()`
   - بازنویسی کامل endpoint `/ai/recommend-slot` با استفاده از recommender جدید
   - تصحیح تمام فراخوانی‌های `compute_ai_priority()` برای تبدیل value_score

---

## 🧪 نتایج تست‌ها

```bash
pytest tests/test_recommend_slot_has_real_doctor.py \
       tests/test_confidence_range_and_variance.py \
       tests/test_value_score_nonzero.py \
       tests/test_persian_encoding_ok.py -v
```

**نتیجه:**
✅ **12 از 12 تست پاس شد**

```
✓ test_recommend_slot_has_real_doctor
✓ test_recommend_slot_multiple_doctors
✓ test_confidence_in_valid_range
✓ test_confidence_has_variance
✓ test_confidence_sorted_descending
✓ test_value_score_nonzero
✓ test_value_score_in_recommend_slot
✓ test_value_score_varies_by_patient
✓ test_persian_encoding_in_score_patient
✓ test_persian_encoding_in_recommend_slot
✓ test_utf8_content_type
✓ test_no_double_encoding
```

---

## 🚀 نحوه استفاده

### 1. راه‌اندازی سرور

```bash
# Windows PowerShell
$env:CRM_MODE="mock"
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Linux/Mac
export CRM_MODE=mock
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. تست endpoint

```bash
curl -X POST "http://localhost:8000/ai/recommend-slot?patient_id=1&service_id=TREATMENT_5&days_ahead=7&max_slots=3"
```

### 3. نتیجه نمونه

```json
{
  "patient_id": "1",
  "service_id": "TREATMENT_5",
  "urgency_level": "high",
  "explain": {
    "priority_score": 93,
    "value_score": 80,
    "risk_no_show": 0.1,
    "risk_late_payment": 0.15,
    "reason_codes": ["CASH_PAYMENT", "HIGH_VALUE", "URGENT_TREATMENT"]
  },
  "recommended_slots": [
    {
      "start_datetime": "2026-02-07T09:00:00+00:00",
      "end_datetime": "2026-02-07T09:30:00+00:00",
      "doctor_id": "D006",
      "doctor_name": "دکتر رضایی",
      "confidence": 0.90,
      "reason_codes": ["AVAILABLE_SOON", "MORNING_SLOT", "HIGH_PRIORITY_MATCH"]
    },
    {
      "start_datetime": "2026-02-08T10:00:00+00:00",
      "end_datetime": "2026-02-08T10:30:00+00:00",
      "doctor_id": "D003",
      "doctor_name": "دکتر صادقی",
      "confidence": 0.85,
      "reason_codes": ["AVAILABLE_SOON", "MORNING_SLOT", "TOP_RATED_DOCTOR"]
    },
    {
      "start_datetime": "2026-02-09T14:00:00+00:00",
      "end_datetime": "2026-02-09T14:30:00+00:00",
      "doctor_id": "D006",
      "doctor_name": "دکتر رضایی",
      "confidence": 0.75,
      "reason_codes": ["AFTERNOON_SLOT", "LOW_DOCTOR_LOAD"]
    }
  ]
}
```

---

## 📊 مقایسه قبل/بعد

| ویژگی | قبل | بعد |
|------|-----|-----|
| **doctor_id** | `"AUTO"` | `"D006"` (واقعی) |
| **doctor_name** | `null` | `"دکتر رضایی"` (واقعی) |
| **confidence** | همه `1.0` | متغیر: `0.90, 0.85, 0.75` |
| **value_score** | همه `0` | متغیر: `40-100` |
| **تنوع slot** | همه صبح یک روز | پخش در روزها و دکترهای مختلف |
| **منطق ranking** | فقط زمانی | confidence + diversity + priority |

---

## 🎯 نتیجه‌گیری

✅ **تمام موارد درخواستی پیاده‌سازی شد:**

- [x] Doctor assignment واقعی (A)
- [x] Confidence scoring با محدوده 0-1 و variance (B)
- [x] Ranking و diversity بهبود یافته (C)
- [x] Value score non-zero و معنادار (D)
- [x] Encoding فارسی بدون مشکل (E)
- [x] تست‌های جامع (F)

**Endpoint `/ai/recommend-slot` حالا آماده production است!** 🚀

---

## 🔄 مراحل بعدی (اختیاری)

1. **افزودن Machine Learning:**
   - استفاده از مدل ML برای پیش‌بینی بهترین slot بر اساس تاریخچه
   - Fine-tuning confidence scoring با داده‌های واقعی

2. **بهبود Diversity:**
   - لحاظ کردن specialty دکتر
   - اولویت‌بندی بر اساس تجربه دکتر

3. **A/B Testing:**
   - مقایسه این ranking با ranking قبلی
   - جمع‌آوری feedback از کاربران

4. **Integration با CRM واقعی:**
   - جایگزینی mock client با live client
   - تست با داده‌های production

---

## 📞 پشتیبانی

برای سوالات یا مشکلات، به فایل‌های زیر مراجعه کنید:
- `QUICKSTART.md` - راهنمای شروع سریع
- `AI_CORE_HARDENING_SUMMARY.md` - خلاصه فاز قبلی
- `NOTES.md` - یادداشت‌های توسعه

---

**تاریخ تکمیل:** 2026-02-06  
**نسخه:** 1.1.0 (Production-Grade Slots)
