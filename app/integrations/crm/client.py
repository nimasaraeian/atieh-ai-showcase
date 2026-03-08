"""CRM Client interface for fetching patient and appointment data.

This module defines the interface for CRM integration.
Actual implementation will be added when CRM API details are available.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, date


class CRMClient:
    """
    Client for interacting with the clinic CRM system.
    
    This is an interface definition. Actual implementation will connect
    to the real CRM API (REST, SOAP, database, etc.) based on the clinic's system.
    """
    
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize CRM client.
        
        Args:
            base_url: CRM API base URL
            api_key: Authentication API key
        """
        self.base_url = base_url
        self.api_key = api_key
    
    def get_patient(self, patient_id: str | int) -> Dict[str, Any]:
        """
        Fetch patient basic information from CRM.
        
        Args:
            patient_id: Unique patient identifier
            
        Returns:
            Dictionary with patient information:
            {
                'patient_id': str | int,
                'full_name': str,
                'phone': str,
                'email': str | None,
                'date_of_birth': str | None,
                'gender': str | None,
                'registration_date': str | None,
                'last_visit_date': str | None,
                'notes': str | None
            }
            
        Raises:
            NotImplementedError: When real CRM integration is not yet implemented
            
        TODO:
        - Implement actual CRM API call
        - Add authentication headers
        - Handle API errors and timeouts
        - Add retry logic
        - Cache patient data if appropriate
        """
        raise NotImplementedError(
            "CRM integration not implemented. Use MockCRMClient for testing."
        )
    
    def get_patient_insurance(self, patient_id: str | int) -> Optional[str]:
        """
        Fetch patient's current insurance information.
        
        Args:
            patient_id: Unique patient identifier
            
        Returns:
            Insurance company name, or None if no insurance
            
        TODO:
        - Implement CRM insurance lookup
        - Handle multiple insurance policies
        - Return insurance validity dates
        - Include coverage details if available
        """
        raise NotImplementedError(
            "CRM integration not implemented. Use MockCRMClient for testing."
        )
    
    def get_patient_unfinished(self, patient_id: str | int) -> List[Dict[str, Any]]:
        """
        Fetch patient's unfinished/pending treatments.
        
        Args:
            patient_id: Unique patient identifier
            
        Returns:
            List of unfinished treatment dictionaries:
            [{
                'treatment_id': str | int,
                'title': str,
                'start_date': str,
                'expected_completion': str | None,
                'urgency': str,  # high/medium/low
                'notes': str | None
            }]
            
        TODO:
        - Implement CRM treatment history lookup
        - Filter only incomplete/pending treatments
        - Sort by urgency or date
        - Include treatment plan details
        """
        raise NotImplementedError(
            "CRM integration not implemented. Use MockCRMClient for testing."
        )
    
    def get_patient_preferences(self, patient_id: str | int) -> Dict[str, Any]:
        """
        Fetch patient scheduling preferences.
        
        Args:
            patient_id: Unique patient identifier
            
        Returns:
            Dictionary with preferences:
            {
                'preferred_doctor': str | None,
                'preferred_weekdays': List[str] | None,
                'preferred_time_of_day': str | None,  # morning/afternoon/evening
                'notes': str | None
            }
            
        TODO:
        - Implement CRM preferences lookup
        - Include historical booking patterns
        - Consider no-show history
        - Include accessibility requirements
        """
        raise NotImplementedError(
            "CRM integration not implemented. Use MockCRMClient for testing."
        )
    
    def get_existing_appointments(
        self,
        start_date: date,
        end_date: date,
        doctor_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch existing appointments in date range.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            doctor_name: Optional filter by doctor
            
        Returns:
            List of appointment dictionaries:
            [{
                'appointment_id': str | int,
                'patient_id': str | int,
                'doctor_name': str,
                'date': str,
                'time': str,
                'duration_minutes': int,
                'service': str,
                'status': str  # scheduled/completed/cancelled/no-show
            }]
            
        TODO:
        - Implement CRM appointments query
        - Add filtering by status
        - Include room/equipment bookings
        - Handle recurring appointments
        """
        raise NotImplementedError(
            "CRM integration not implemented. Use MockCRMClient for testing."
        )
    
    def get_payment_behavior(self, patient_id: str | int) -> str:
        """
        Get patient payment behavior tag.
        
        Args:
            patient_id: Unique patient identifier
            
        Returns:
            Payment behavior: 'good', 'fair', 'poor', or 'unknown'
            
        TODO:
        - Implement payment history analysis
        - Calculate payment reliability score
        - Include outstanding balance info
        - Consider payment plan status
        """
        raise NotImplementedError(
            "CRM integration not implemented. Use MockCRMClient for testing."
        )
