"""
CRM Client Abstract Interface
==============================
Defines the contract that all CRM clients (mock or real) must implement.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime


class CRMClientInterface(ABC):
    """Abstract base class for CRM client implementations."""
    
    @abstractmethod
    def fetch_patients(
        self,
        updated_since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch patient records from CRM.
        
        Args:
            updated_since: Only return patients updated after this datetime
            limit: Maximum number of records to return
            
        Returns:
            List of patient dictionaries
        """
        pass
    
    @abstractmethod
    def fetch_appointments(
        self,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
        patient_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch appointment records from CRM.
        
        Args:
            from_dt: Start date filter
            to_dt: End date filter
            patient_id: Filter by patient ID
            status: Filter by status
            limit: Maximum number of records to return
            
        Returns:
            List of appointment dictionaries
        """
        pass
    
    @abstractmethod
    def fetch_payments(
        self,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
        patient_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch payment records from CRM.
        
        Args:
            from_dt: Start date filter
            to_dt: End date filter
            patient_id: Filter by patient ID
            limit: Maximum number of records to return
            
        Returns:
            List of payment dictionaries
        """
        pass
    
    @abstractmethod
    def fetch_doctors(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Fetch doctor/provider records from CRM.
        
        Args:
            active_only: Only return active doctors
            
        Returns:
            List of doctor dictionaries
        """
        pass
    
    @abstractmethod
    def fetch_schedules(
        self,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
        doctor_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch doctor schedule/availability records from CRM.
        
        Args:
            from_dt: Start date filter
            to_dt: End date filter
            doctor_id: Filter by doctor ID
            
        Returns:
            List of schedule dictionaries
        """
        pass
    
    @abstractmethod
    def fetch_blocks(
        self,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
        doctor_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch blocking events (vacations, meetings, etc.) from CRM.
        
        Args:
            from_dt: Start date filter
            to_dt: End date filter
            doctor_id: Filter by doctor ID
            
        Returns:
            List of blocking event dictionaries
        """
        pass
    
    def get_patient_history(self, patient_id: str) -> Dict[str, Any]:
        """
        Get complete patient history (appointments + payments).
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            Dictionary with appointments and payments
        """
        appointments = self.fetch_appointments(patient_id=patient_id)
        payments = self.fetch_payments(patient_id=patient_id)
        
        return {
            "patient_id": patient_id,
            "appointments": appointments,
            "payments": payments
        }
    
    def health_check(self) -> bool:
        """
        Check if CRM connection is healthy.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            # Try to fetch minimal data as health check
            self.fetch_patients(limit=1)
            return True
        except Exception:
            return False
