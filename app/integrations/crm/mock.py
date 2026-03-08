"""Mock CRM client for testing without real CRM connection."""
from typing import Optional, Dict, Any, List
from datetime import date
from app.integrations.crm.client import CRMClient


class MockCRMClient(CRMClient):
    """
    Mock CRM client that returns sample data for testing.
    
    This allows the engine to be tested without a real CRM connection.
    Replace with real CRMClient implementation when integrating with actual CRM.
    """
    
    # Sample patient database
    MOCK_PATIENTS = {
        '123': {
            'patient_id': '123',
            'full_name': 'علی احمدی',
            'phone': '09121234567',
            'email': 'ali.ahmadi@example.com',
            'date_of_birth': '1990-05-15',
            'gender': 'male',
            'registration_date': '2020-01-10',
            'last_visit_date': '2025-12-15',
            'notes': 'Prefers morning appointments'
        },
        '456': {
            'patient_id': '456',
            'full_name': 'فاطمه محمدی',
            'phone': '09127654321',
            'email': 'fateme@example.com',
            'date_of_birth': '1985-08-20',
            'gender': 'female',
            'registration_date': '2019-06-05',
            'last_visit_date': '2026-01-20',
            'notes': 'Anxious about dental procedures'
        },
        '789': {
            'patient_id': '789',
            'full_name': 'محمد رضایی',
            'phone': '09139876543',
            'email': None,
            'date_of_birth': '1975-03-10',
            'gender': 'male',
            'registration_date': '2018-03-15',
            'last_visit_date': '2025-11-30',
            'notes': None
        }
    }
    
    # Sample insurance data
    MOCK_INSURANCE = {
        '123': 'ایران',
        '456': 'تامین اجتماعی',
        '789': None
    }
    
    # Sample unfinished treatments
    MOCK_UNFINISHED = {
        '123': [
            {
                'treatment_id': 'T001',
                'title': 'درمان ریشه',
                'start_date': '2025-12-01',
                'expected_completion': '2026-02-15',
                'urgency': 'high',
                'notes': 'Session 2 of 3 completed'
            }
        ],
        '456': [
            {
                'treatment_id': 'T002',
                'title': 'ایمپلنت',
                'start_date': '2025-10-15',
                'expected_completion': '2026-03-01',
                'urgency': 'medium',
                'notes': 'Waiting for implant integration'
            },
            {
                'treatment_id': 'T003',
                'title': 'جراحی',
                'start_date': '2025-11-20',
                'expected_completion': '2026-02-10',
                'urgency': 'high',
                'notes': 'Follow-up surgery needed'
            }
        ],
        '789': []
    }
    
    # Sample preferences
    MOCK_PREFERENCES = {
        '123': {
            'preferred_doctor': 'دکتر احمدی',
            'preferred_weekdays': ['شنبه', 'یکشنبه'],
            'preferred_time_of_day': 'morning',
            'notes': 'Works during evenings, prefers morning'
        },
        '456': {
            'preferred_doctor': 'دکتر نعمتی',
            'preferred_weekdays': ['سه شنبه', 'چهارشنبه'],
            'preferred_time_of_day': 'evening',
            'notes': 'Prefers female doctors'
        },
        '789': {
            'preferred_doctor': None,
            'preferred_weekdays': None,
            'preferred_time_of_day': None,
            'notes': None
        }
    }
    
    # Sample payment behavior
    MOCK_PAYMENT_BEHAVIOR = {
        '123': 'good',
        '456': 'good',
        '789': 'fair'
    }
    
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        """Initialize mock CRM client."""
        super().__init__(base_url, api_key)
    
    @property
    def patients(self) -> Dict[str, Dict[str, Any]]:
        """Access mock patients database."""
        return self.MOCK_PATIENTS
    
    @property
    def insurances(self) -> Dict[str, Optional[str]]:
        """Access mock insurance data."""
        return self.MOCK_INSURANCE
    
    @property
    def unfinished_treatments(self) -> Dict[str, List[Dict[str, Any]]]:
        """Access mock unfinished treatments."""
        return self.MOCK_UNFINISHED
    
    @property
    def preferences(self) -> Dict[str, Dict[str, Any]]:
        """Access mock patient preferences."""
        return self.MOCK_PREFERENCES
    
    @property
    def payment_behaviors(self) -> Dict[str, str]:
        """Access mock payment behaviors."""
        return self.MOCK_PAYMENT_BEHAVIOR
    
    def get_patient(self, patient_id: str | int) -> Dict[str, Any]:
        """Fetch mock patient data."""
        patient_id = str(patient_id)
        if patient_id not in self.MOCK_PATIENTS:
            raise ValueError(f"Patient {patient_id} not found in mock database")
        return self.MOCK_PATIENTS[patient_id].copy()
    
    def get_patient_insurance(self, patient_id: str | int) -> Optional[str]:
        """Fetch mock patient insurance."""
        patient_id = str(patient_id)
        return self.MOCK_INSURANCE.get(patient_id)
    
    def get_patient_unfinished(self, patient_id: str | int) -> List[Dict[str, Any]]:
        """Fetch mock unfinished treatments."""
        patient_id = str(patient_id)
        return self.MOCK_UNFINISHED.get(patient_id, []).copy()
    
    def get_patient_preferences(self, patient_id: str | int) -> Dict[str, Any]:
        """Fetch mock patient preferences."""
        patient_id = str(patient_id)
        return self.MOCK_PREFERENCES.get(patient_id, {}).copy()
    
    def get_existing_appointments(
        self,
        start_date: date,
        end_date: date,
        doctor_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch mock existing appointments."""
        # Return empty list for mock - no existing appointments
        return []
    
    def get_payment_behavior(self, patient_id: str | int) -> str:
        """Get mock payment behavior."""
        patient_id = str(patient_id)
        return self.MOCK_PAYMENT_BEHAVIOR.get(patient_id, 'unknown')
