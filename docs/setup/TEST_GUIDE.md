# 🧪 راهنمای تست سیستم

## گام 1: راه‌اندازی سرور

ابتدا سرور را اجرا کنید:

```bash
uvicorn main:app --reload
```

سرور روی آدرس `http://localhost:8000` اجرا می‌شود.

## گام 2: اجرای تست‌های خودکار

### تست کامل (10 تست)

```bash
python scripts/test_api_complete.py
```

این اسکریپت 10 تست اصلی را اجرا می‌کند:
- ✅ Health Check
- ✅ دریافت لیست بیماران
- ✅ جزئیات یک بیمار
- ✅ دریافت لیست نوبت‌ها
- ✅ انواع پرداخت
- ✅ انواع درمان
- ✅ امتیازدهی AI به بیمار
- ✅ پیشنهاد زمان نوبت
- ✅ جستجوی بیماران
- ✅ وضعیت Import

## گام 3: تست دستی با مرورگر

بعد از اجرای سرور، این لینک‌ها را در مرورگر باز کنید:

### 📄 مستندات API
```
http://localhost:8000/docs
```

### 🏥 تست‌های اصلی

1. **سلامت سیستم**
   ```
   http://localhost:8000/health
   ```

2. **لیست بیماران (5 نفر اول)**
   ```
   http://localhost:8000/patients?limit=5
   ```

3. **جزئیات بیمار شماره 1**
   ```
   http://localhost:8000/patients/1
   ```

4. **امتیازدهی AI به بیمار**
   ```
   http://localhost:8000/ai/score-patient?patient_id=1
   ```

5. **پیشنهاد زمان نوبت**
   ```
   http://localhost:8000/appointments/suggest-time?treatment_type=TREATMENT_10&patient_id=1&max_suggestions=5
   ```

6. **جستجوی بیمار**
   ```
   http://localhost:8000/patients?search=Ali&limit=5
   ```

7. **انواع پرداخت**
   ```
   http://localhost:8000/payment-types
   ```

8. **لیست نوبت‌ها**
   ```
   http://localhost:8000/appointments?limit=10&future_only=false
   ```

## گام 4: تست با Postman یا curl

### دریافت لیست بیماران
```bash
curl -X GET "http://localhost:8000/patients?limit=5" -H "accept: application/json"
```

### امتیازدهی AI
```bash
curl -X POST "http://localhost:8000/ai/score-patient?patient_id=1" -H "accept: application/json"
```

### پیشنهاد زمان نوبت
```bash
curl -X GET "http://localhost:8000/appointments/suggest-time?treatment_type=TREATMENT_10&patient_id=1&max_suggestions=3" -H "accept: application/json"
```

## 📊 نتیجه مورد انتظار

اگر همه چیز درست کار کند:
- ✅ Health check باید status "ok" برگرداند
- ✅ Patients endpoint باید لیست بیماران را برگرداند
- ✅ AI scoring باید امتیاز و ریسک‌ها را محاسبه کند
- ✅ Suggest time باید زمان‌های خالی پیشنهاد دهد

## ⚠️ رفع مشکلات رایج

### سرور اجرا نمی‌شود
```bash
# بررسی نصب بودن وابستگی‌ها
pip install -r requirements.txt

# اجرای مجدد
uvicorn main:app --reload
```

### پورت 8000 اشغال است
```bash
# استفاده از پورت دیگر
uvicorn main:app --reload --port 8001
```

### خطای دیتابیس
```bash
# بررسی وجود فایل دیتابیس
dir atieh_clinic.db
```

## 🎯 معیارهای موفقیت

سیستم زمانی **100% سالم** است که:
1. ✅ سرور بدون خطا اجرا شود
2. ✅ تمام 10 تست Pass شوند
3. ✅ API documentation در `/docs` قابل دسترسی باشد
4. ✅ AI scoring برای بیماران کار کند
5. ✅ پیشنهاد زمان نوبت موفق باشد
