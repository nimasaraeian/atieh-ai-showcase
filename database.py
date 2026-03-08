from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from models import Base
import os

# تنظیمات دیتابیس
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///atieh_clinic.db")

# Create engine with SQLite optimizations
if "sqlite" in DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "check_same_thread": False,
            "timeout": 30
        }
    )
    
    # Configure SQLite for better concurrency and prevent locking
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")  # Write-Ahead Logging for better concurrency
        cursor.execute("PRAGMA synchronous=NORMAL;")  # Balance between safety and speed
        cursor.execute("PRAGMA busy_timeout=5000;")  # Wait up to 5 seconds if database is locked
        cursor.close()
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """ایجاد جداول دیتابیس"""
    Base.metadata.create_all(bind=engine)
    _ensure_indexes()


def _ensure_indexes():
    """Create performance indexes that are not declared on the ORM models."""
    indexes = [
        # Needed by extract_features() and all per-patient appointment queries
        "CREATE INDEX IF NOT EXISTS idx_appointments_patient_id ON appointments(patient_id)",
        # Needed by /ai/top-patients JOIN filter on appointment_date range
        "CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(appointment_date)",
        # Needed by extract_features() status IN ('completed','cancelled') filter
        "CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status)",
        # Needed by /ai/top-patients JOIN from stg_appointments on appointment_id
        "CREATE INDEX IF NOT EXISTS idx_stg_appt_appointment_id ON stg_appointments(appointment_id)",
    ]
    with engine.connect() as conn:
        for ddl in indexes:
            conn.execute(text(ddl))
        conn.commit()


def get_db() -> Session:
    """دریافت session دیتابیس"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()







