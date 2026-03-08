"""
Pytest Configuration and Fixtures
===================================
Provides test database setup, fixtures, and dependency overrides for all tests.
"""
import pytest
import os
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient
from datetime import datetime, timezone

# Set test environment variables BEFORE importing app
os.environ['CRM_MODE'] = 'mock'
os.environ['ENGINE_VERSION'] = 'v1'  # Use v1 for stable tests

# Import after setting env vars
from main import app
from models import Base, Patient, Appointment, PaymentType, TreatmentType
from database import get_db


# ==============================================================================
# Test Database Configuration
# ==============================================================================

def get_test_engine():
    """
    Create an in-memory SQLite database with StaticPool.
    
    StaticPool ensures:
    - Same connection used across threads (safe for SQLite :memory:)
    - No WinError 32 (file in use) issues
    - Fast tests (in-memory)
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False  # Set to True for SQL debugging
    )
    return engine


# ==============================================================================
# Session Fixtures
# ==============================================================================

@pytest.fixture(scope="function")
def test_engine():
    """Create a fresh test database engine for each test."""
    engine = get_test_engine()
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_db_session(test_engine):
    """
    Create a fresh database session for each test.
    
    This fixture:
    - Creates tables before test
    - Provides a clean session
    - Rolls back after test (if using transactions)
    - Closes session properly
    """
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestSessionLocal()
    
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def override_get_db_fixture(test_db_session):
    """
    Override FastAPI's get_db dependency with test session.
    
    This ensures all API endpoints use the test database.
    """
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass  # Session cleanup handled by test_db_session fixture
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield
    
    # Cleanup: remove override after test
    app.dependency_overrides.clear()


# ==============================================================================
# Test Client Fixture
# ==============================================================================

@pytest.fixture(scope="function")
def client(override_get_db_fixture):
    """
    Create FastAPI test client with overridden database dependency.
    
    This client:
    - Uses test database (not production atieh_clinic.db)
    - Automatically handles request/response cycles
    - Cleans up after each test
    """
    with TestClient(app) as test_client:
        yield test_client


# ==============================================================================
# Sample Data Fixtures
# ==============================================================================

@pytest.fixture(scope="function")
def seed_patients(test_db_session: Session):
    """
    Seed test database with 3 sample patients.
    
    Patient IDs: 1, 2, 3
    """
    patients = [
        Patient(
            id=1,
            name="علی احمدی",
            phone="09121234567",
            national_id="1234567890",
            payment_type=PaymentType.CASH,
            first_visit_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        ),
        Patient(
            id=2,
            name="زهرا محمدی",
            phone="09129876543",
            national_id="9876543210",
            payment_type=PaymentType.INSURANCE_5,
            first_visit_date=datetime(2024, 6, 1, tzinfo=timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        ),
        Patient(
            id=3,
            name="حسین رضایی",
            phone="09351112222",
            national_id="1122334455",
            payment_type=PaymentType.INSURANCE_15,
            first_visit_date=datetime(2025, 11, 1, tzinfo=timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
    ]
    
    for patient in patients:
        test_db_session.add(patient)
    
    test_db_session.commit()
    
    # Refresh to get database-assigned values
    for patient in patients:
        test_db_session.refresh(patient)
    
    return patients


@pytest.fixture(scope="function")
def seed_appointments(test_db_session: Session, seed_patients):
    """
    Seed test database with sample appointments.
    
    Depends on seed_patients fixture.
    """
    appointments = [
        Appointment(
            patient_id=1,
            appointment_date=datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc),
            duration_minutes=30,
            payment_type=PaymentType.CASH,
            treatment_type=TreatmentType.TREATMENT_5,
            priority_score=85.0,
            status="pending",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        ),
        Appointment(
            patient_id=2,
            appointment_date=datetime(2026, 3, 2, 14, 0, tzinfo=timezone.utc),
            duration_minutes=60,
            payment_type=PaymentType.INSURANCE_5,
            treatment_type=TreatmentType.TREATMENT_10,
            priority_score=70.0,
            status="confirmed",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
    ]
    
    for appointment in appointments:
        test_db_session.add(appointment)
    
    test_db_session.commit()
    
    return appointments


# ==============================================================================
# Combined Fixture for Convenience
# ==============================================================================

@pytest.fixture(scope="function")
def seeded_db(test_db_session, seed_patients, seed_appointments):
    """
    Convenience fixture that provides a fully seeded test database.
    
    Includes:
    - 3 patients (IDs 1, 2, 3)
    - 2 appointments
    """
    return {
        'session': test_db_session,
        'patients': seed_patients,
        'appointments': seed_appointments
    }


# ==============================================================================
# Pytest Configuration
# ==============================================================================

def pytest_configure(config):
    """Pytest hook to configure test session."""
    # Ensure test database files don't interfere
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )


def pytest_collection_modifyitems(config, items):
    """Pytest hook to modify test collection."""
    # Add markers automatically based on test names
    for item in items:
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        if "slow" in item.nodeid:
            item.add_marker(pytest.mark.slow)


# ==============================================================================
# Session-wide Cleanup
# ==============================================================================

@pytest.fixture(scope="session", autouse=True)
def cleanup_test_artifacts():
    """Clean up any test artifacts created during test session."""
    yield
    
    # Clean up any test database files that might have been created
    test_db_files = [
        "test_atieh.db",
        "test_atieh.db-journal",
        "test.db",
        "test.db-journal"
    ]
    
    for db_file in test_db_files:
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
                print(f"Cleaned up test database file: {db_file}")
            except Exception as e:
                print(f"Warning: Could not remove {db_file}: {e}")


# ==============================================================================
# Configuration Summary
# ==============================================================================

"""
Usage Examples:
---------------

1. Simple test with client:
    def test_health(client):
        response = client.get("/health")
        assert response.status_code == 200

2. Test with seeded data:
    def test_get_patients(client, seed_patients):
        response = client.get("/patients")
        assert len(response.json()) == 3

3. Test with custom data:
    def test_create_patient(client, test_db_session):
        # Add custom test data
        patient = Patient(name="Test", phone="123")
        test_db_session.add(patient)
        test_db_session.commit()
        
        # Test endpoint
        response = client.get(f"/patients/{patient.id}")
        assert response.status_code == 200

4. Test with full seeded database:
    def test_appointments(client, seeded_db):
        patients = seeded_db['patients']
        response = client.get(f"/patients/{patients[0].id}")
        assert response.status_code == 200
"""
