"""
اسکریپت migration برای افزودن فیلد payment_type به جدول patients
و فیلدهای AI و outcome logging به جدول appointments
"""
import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import sqlite3
import os
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

def migrate_database():
    """افزودن فیلد payment_type به جدول patients"""
    db_path = "atieh_clinic.db"
    
    if not os.path.exists(db_path):
        print("Database not found. New tables will be created when server starts.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # بررسی وجود فیلد payment_type
        cursor.execute("PRAGMA table_info(patients)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'payment_type' not in columns:
            print("Adding payment_type field...")
            # افزودن فیلد payment_type
            try:
                cursor.execute("ALTER TABLE patients ADD COLUMN payment_type VARCHAR(20)")
                conn.commit()
                print("Field payment_type added successfully.")
            except sqlite3.OperationalError as e:
                if "duplicate column" in str(e).lower():
                    print("Field payment_type already exists.")
                else:
                    print(f"Error adding field: {e}")
        else:
            print("Field payment_type already exists.")
        
        # بررسی و افزودن duration_minutes به appointments
        cursor.execute("PRAGMA table_info(appointments)")
        appointment_columns = [row[1] for row in cursor.fetchall()]
        
        if 'duration_minutes' not in appointment_columns:
            print("Adding duration_minutes field...")
            try:
                cursor.execute("ALTER TABLE appointments ADD COLUMN duration_minutes INTEGER DEFAULT 30")
                conn.commit()
                print("Field duration_minutes added successfully.")
            except sqlite3.OperationalError as e:
                if "duplicate column" in str(e).lower():
                    print("Field duration_minutes already exists.")
                else:
                    print(f"Error adding duration_minutes: {e}")
        else:
            print("Field duration_minutes already exists.")
        
        # افزودن فیلدهای AI و outcome logging به appointments
        print("\nChecking AI and outcome logging fields...")
        
        # استفاده از SQLAlchemy inspector برای بررسی دقیق‌تر
        try:
            from sqlalchemy import create_engine, inspect
            engine = create_engine(f'sqlite:///{db_path}')
            inspector = inspect(engine)
            columns = [col['name'] for col in inspector.get_columns('appointments')]
            
            with engine.connect() as conn:
                # AI-related fields
                if 'ai_priority_score' not in columns:
                    print("Adding ai_priority_score field...")
                    conn.execute("ALTER TABLE appointments ADD COLUMN ai_priority_score FLOAT")
                    conn.commit()
                    print("Field ai_priority_score added successfully.")
                else:
                    print("Field ai_priority_score already exists.")
                
                # Outcome logging fields
                if 'did_patient_show_up' not in columns:
                    print("Adding did_patient_show_up field...")
                    conn.execute("ALTER TABLE appointments ADD COLUMN did_patient_show_up BOOLEAN")
                    conn.commit()
                    print("Field did_patient_show_up added successfully.")
                else:
                    print("Field did_patient_show_up already exists.")
                
                if 'paid_on_time' not in columns:
                    print("Adding paid_on_time field...")
                    conn.execute("ALTER TABLE appointments ADD COLUMN paid_on_time BOOLEAN")
                    conn.commit()
                    print("Field paid_on_time added successfully.")
                else:
                    print("Field paid_on_time already exists.")
                
                if 'payment_delay_days' not in columns:
                    print("Adding payment_delay_days field...")
                    conn.execute("ALTER TABLE appointments ADD COLUMN payment_delay_days INTEGER")
                    conn.commit()
                    print("Field payment_delay_days added successfully.")
                else:
                    print("Field payment_delay_days already exists.")
                
                if 'final_amount_paid' not in columns:
                    print("Adding final_amount_paid field...")
                    conn.execute("ALTER TABLE appointments ADD COLUMN final_amount_paid FLOAT")
                    conn.commit()
                    print("Field final_amount_paid added successfully.")
                else:
                    print("Field final_amount_paid already exists.")
                
                if 'cancellation_reason' not in columns:
                    print("Adding cancellation_reason field...")
                    conn.execute("ALTER TABLE appointments ADD COLUMN cancellation_reason TEXT")
                    conn.commit()
                    print("Field cancellation_reason added successfully.")
                else:
                    print("Field cancellation_reason already exists.")
            
            engine.dispose()
        except Exception as e:
            print(f"Warning: Could not use SQLAlchemy inspector, using direct SQL: {e}")
            # Fallback به روش مستقیم SQL
            cursor.execute("PRAGMA table_info(appointments)")
            appointment_columns = [row[1] for row in cursor.fetchall()]
            
            if 'ai_priority_score' not in appointment_columns:
                try:
                    cursor.execute("ALTER TABLE appointments ADD COLUMN ai_priority_score FLOAT")
                    conn.commit()
                    print("Field ai_priority_score added successfully.")
                except sqlite3.OperationalError:
                    print("Field ai_priority_score already exists.")
            
            if 'did_patient_show_up' not in appointment_columns:
                try:
                    cursor.execute("ALTER TABLE appointments ADD COLUMN did_patient_show_up BOOLEAN")
                    conn.commit()
                    print("Field did_patient_show_up added successfully.")
                except sqlite3.OperationalError:
                    print("Field did_patient_show_up already exists.")
            
            if 'paid_on_time' not in appointment_columns:
                try:
                    cursor.execute("ALTER TABLE appointments ADD COLUMN paid_on_time BOOLEAN")
                    conn.commit()
                    print("Field paid_on_time added successfully.")
                except sqlite3.OperationalError:
                    print("Field paid_on_time already exists.")
            
            if 'payment_delay_days' not in appointment_columns:
                try:
                    cursor.execute("ALTER TABLE appointments ADD COLUMN payment_delay_days INTEGER")
                    conn.commit()
                    print("Field payment_delay_days added successfully.")
                except sqlite3.OperationalError:
                    print("Field payment_delay_days already exists.")
            
            if 'final_amount_paid' not in appointment_columns:
                try:
                    cursor.execute("ALTER TABLE appointments ADD COLUMN final_amount_paid FLOAT")
                    conn.commit()
                    print("Field final_amount_paid added successfully.")
                except sqlite3.OperationalError:
                    print("Field final_amount_paid already exists.")
            
            if 'cancellation_reason' not in appointment_columns:
                try:
                    cursor.execute("ALTER TABLE appointments ADD COLUMN cancellation_reason TEXT")
                    conn.commit()
                    print("Field cancellation_reason added successfully.")
                except sqlite3.OperationalError:
                    print("Field cancellation_reason already exists.")
        
        conn.close()
        
    except Exception as e:
        print(f"Error in migration: {e}")
        conn.close()
        raise

if __name__ == "__main__":
    migrate_database()

