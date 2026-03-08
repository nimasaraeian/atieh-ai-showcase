"""
Mock CRM Client Implementation
===============================
Reads data from JSON files in data/mock/ directory.
Used for testing and development before real CRM integration.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .interface import CRMClientInterface

logger = logging.getLogger(__name__)


class MockCRMClient(CRMClientInterface):
    """Mock CRM client that reads from JSON files."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize mock CRM client.
        
        Args:
            data_dir: Path to mock data directory. Defaults to data/mock/
        """
        if data_dir is None:
            # Auto-detect data directory
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent.parent
            data_dir = project_root / "data" / "mock"
        
        self.data_dir = Path(data_dir)
        logger.info(f"MockCRMClient initialized with data_dir: {self.data_dir}")
        
        # Lazy-loaded data
        self._patients: Optional[List[Dict]] = None
        self._appointments: Optional[List[Dict]] = None
        self._payments: Optional[List[Dict]] = None
        self._doctors: Optional[List[Dict]] = None
        self._schedules: Optional[List[Dict]] = None
        self._blocks: Optional[List[Dict]] = None
    
    def _load_json(self, filename: str) -> List[Dict]:
        """Load data from JSON file."""
        filepath = self.data_dir / filename
        
        if not filepath.exists():
            logger.warning(f"Mock data file not found: {filepath}")
            return []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.debug(f"Loaded {len(data)} records from {filename}")
            return data
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            return []
    
    def _get_patients(self) -> List[Dict]:
        """Get patients data (lazy load)."""
        if self._patients is None:
            self._patients = self._load_json("patients.json")
        return self._patients
    
    def _get_appointments(self) -> List[Dict]:
        """Get appointments data (lazy load)."""
        if self._appointments is None:
            self._appointments = self._load_json("appointments.json")
        return self._appointments
    
    def _get_payments(self) -> List[Dict]:
        """Get payments data (lazy load)."""
        if self._payments is None:
            self._payments = self._load_json("payments.json")
        return self._payments
    
    def _get_doctors(self) -> List[Dict]:
        """Get doctors data (lazy load)."""
        if self._doctors is None:
            self._doctors = self._load_json("doctors.json")
        return self._doctors
    
    def _get_schedules(self) -> List[Dict]:
        """Get schedules data (lazy load)."""
        if self._schedules is None:
            self._schedules = self._load_json("schedules.json")
        return self._schedules
    
    def _get_blocks(self) -> List[Dict]:
        """Get blocks data (lazy load)."""
        if self._blocks is None:
            self._blocks = self._load_json("blocks.json")
        return self._blocks
    
    def fetch_patients(
        self,
        updated_since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Fetch patient records."""
        patients = self._get_patients()
        
        # Filter by updated_since
        if updated_since:
            patients = [
                p for p in patients
                if datetime.fromisoformat(p['updated_at']) >= updated_since
            ]
        
        # Apply limit
        if limit:
            patients = patients[:limit]
        
        return patients
    
    def fetch_appointments(
        self,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
        patient_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Fetch appointment records."""
        appointments = self._get_appointments()
        
        # Filter by date range
        if from_dt or to_dt:
            filtered = []
            for appt in appointments:
                appt_date = datetime.fromisoformat(appt['appointment_date'])
                # Make timezone-aware if needed for comparison
                if appt_date.tzinfo is None:
                    from datetime import timezone as tz
                    appt_date = appt_date.replace(tzinfo=tz.utc)
                if from_dt and appt_date < from_dt:
                    continue
                if to_dt and appt_date > to_dt:
                    continue
                filtered.append(appt)
            appointments = filtered
        
        # Filter by patient_id
        if patient_id:
            appointments = [a for a in appointments if a['patient_id'] == patient_id]
        
        # Filter by status
        if status:
            appointments = [a for a in appointments if a['status'] == status]
        
        # Apply limit
        if limit:
            appointments = appointments[:limit]
        
        return appointments
    
    def fetch_payments(
        self,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
        patient_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Fetch payment records."""
        payments = self._get_payments()
        
        # Filter by date range (using payment_date)
        if from_dt or to_dt:
            filtered = []
            for pmt in payments:
                if pmt.get('payment_date'):
                    pmt_date = datetime.fromisoformat(pmt['payment_date'])
                    if from_dt and pmt_date < from_dt:
                        continue
                    if to_dt and pmt_date > to_dt:
                        continue
                    filtered.append(pmt)
                elif not from_dt and not to_dt:
                    filtered.append(pmt)
            payments = filtered
        
        # Filter by patient_id
        if patient_id:
            payments = [p for p in payments if p['patient_id'] == patient_id]
        
        # Apply limit
        if limit:
            payments = payments[:limit]
        
        return payments
    
    def fetch_doctors(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Fetch doctor records."""
        doctors = self._get_doctors()
        
        # Filter by active status
        if active_only:
            doctors = [d for d in doctors if d.get('is_active', True)]
        
        return doctors
    
    def fetch_schedules(
        self,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
        doctor_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch schedule records."""
        schedules = self._get_schedules()
        
        # Filter by date range
        if from_dt or to_dt:
            filtered = []
            for sch in schedules:
                sch_date = datetime.strptime(sch['date'], '%Y-%m-%d')
                if from_dt and sch_date < from_dt.replace(hour=0, minute=0, second=0, microsecond=0):
                    continue
                if to_dt and sch_date > to_dt.replace(hour=23, minute=59, second=59, microsecond=999999):
                    continue
                filtered.append(sch)
            schedules = filtered
        
        # Filter by doctor_id
        if doctor_id:
            schedules = [s for s in schedules if s['doctor_id'] == doctor_id]
        
        return schedules
    
    def fetch_blocks(
        self,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
        doctor_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch blocking event records."""
        blocks = self._get_blocks()
        
        # Filter by date range
        if from_dt or to_dt:
            filtered = []
            for blk in blocks:
                blk_start = datetime.fromisoformat(blk['start_datetime'])
                blk_end = datetime.fromisoformat(blk['end_datetime'])
                
                # Check if block overlaps with date range
                if from_dt and blk_end < from_dt:
                    continue
                if to_dt and blk_start > to_dt:
                    continue
                filtered.append(blk)
            blocks = filtered
        
        # Filter by doctor_id
        if doctor_id:
            blocks = [b for b in blocks if b['doctor_id'] == doctor_id]
        
        return blocks
    
    def reload(self):
        """Reload all data from files."""
        self._patients = None
        self._appointments = None
        self._payments = None
        self._doctors = None
        self._schedules = None
        self._blocks = None
        logger.info("Mock CRM data reloaded")
