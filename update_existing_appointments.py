"""
اسکریپت به‌روزرسانی نوبت‌های موجود برای اضافه کردن duration_minutes
"""
from database import SessionLocal, init_db
from models import Appointment

def update_appointments():
    """به‌روزرسانی نوبت‌های موجود"""
    db = SessionLocal()
    
    try:
        # دریافت همه نوبت‌ها
        appointments = db.query(Appointment).all()
        
        updated_count = 0
        for appointment in appointments:
            # اگر duration_minutes تنظیم نشده، مقدار پیش‌فرض را تنظیم می‌کنیم
            if not hasattr(appointment, 'duration_minutes') or appointment.duration_minutes is None:
                appointment.duration_minutes = 30
                updated_count += 1
        
        db.commit()
        print(f"✓ {updated_count} نوبت به‌روزرسانی شد")
        print(f"✓ کل نوبت‌ها: {len(appointments)}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ خطا: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    init_db()  # اطمینان از وجود جداول
    update_appointments()







