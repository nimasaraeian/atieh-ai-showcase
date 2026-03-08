"""
ماژول اتصال به CRM کلینیک
این ماژول امکان همگام‌سازی داده‌ها با سیستم CRM خارجی را فراهم می‌کند
"""
import requests
import os
from typing import Optional, Dict, List, Any
from datetime import datetime
from sqlalchemy.orm import Session
from models import Patient, Appointment
import json
import logging

logger = logging.getLogger(__name__)


class CRMConfig:
    """تنظیمات اتصال به CRM"""
    
    def __init__(self):
        # URL پایه CRM (مثال: https://crm.example.com/api)
        self.base_url = os.getenv("CRM_BASE_URL", "")
        
        # API Key یا Token برای احراز هویت
        self.api_key = os.getenv("CRM_API_KEY", "")
        
        # نوع احراز هویت: "bearer", "api_key", "basic"
        self.auth_type = os.getenv("CRM_AUTH_TYPE", "bearer")
        
        # Username و Password برای Basic Auth (در صورت نیاز)
        self.username = os.getenv("CRM_USERNAME", "")
        self.password = os.getenv("CRM_PASSWORD", "")
        
        # فعال/غیرفعال بودن همگام‌سازی
        self.enabled = os.getenv("CRM_ENABLED", "false").lower() == "true"
        
        # Timeout برای درخواست‌ها (ثانیه)
        self.timeout = int(os.getenv("CRM_TIMEOUT", "30"))
        
        # Endpointهای CRM
        self.endpoints = {
            "patients": os.getenv("CRM_ENDPOINT_PATIENTS", "/patients"),
            "appointments": os.getenv("CRM_ENDPOINT_APPOINTMENTS", "/appointments"),
            "sync": os.getenv("CRM_ENDPOINT_SYNC", "/sync")
        }
    
    def is_configured(self) -> bool:
        """بررسی اینکه آیا CRM تنظیم شده است یا نه"""
        return bool(self.base_url and self.api_key and self.enabled)
    
    def get_headers(self) -> Dict[str, str]:
        """دریافت headerهای لازم برای احراز هویت"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if self.auth_type == "bearer":
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif self.auth_type == "api_key":
            headers["X-API-Key"] = self.api_key
        elif self.auth_type == "basic":
            # Basic Auth باید از طریق requests.auth.HTTPBasicAuth استفاده شود
            pass
        
        return headers
    
    def get_auth(self) -> Optional[Any]:
        """دریافت اطلاعات احراز هویت"""
        if self.auth_type == "basic" and self.username and self.password:
            from requests.auth import HTTPBasicAuth
            return HTTPBasicAuth(self.username, self.password)
        return None


class CRMIntegration:
    """کلاس اصلی برای اتصال و همگام‌سازی با CRM"""
    
    def __init__(self):
        self.config = CRMConfig()
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Optional[Dict]:
        """ارسال درخواست به CRM"""
        if not self.config.is_configured():
            logger.warning("CRM is not configured or not enabled")
            return None
        
        url = f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = self.config.get_headers()
        auth = self.config.get_auth()
        
        try:
            response = requests.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers,
                auth=auth,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to CRM: {e}")
            return None
    
    def sync_patient(self, patient: Patient) -> bool:
        """همگام‌سازی یک بیمار با CRM"""
        if not self.config.is_configured():
            return False
        
        # تبدیل Patient به فرمت CRM
        patient_data = self._convert_patient_to_crm_format(patient)
        
        # ارسال به CRM
        result = self._make_request(
            method="POST",
            endpoint=self.config.endpoints["patients"],
            data=patient_data
        )
        
        return result is not None
    
    def sync_appointment(self, appointment: Appointment) -> bool:
        """همگام‌سازی یک نوبت با CRM"""
        if not self.config.is_configured():
            return False
        
        # تبدیل Appointment به فرمت CRM
        appointment_data = self._convert_appointment_to_crm_format(appointment)
        
        # ارسال به CRM
        result = self._make_request(
            method="POST",
            endpoint=self.config.endpoints["appointments"],
            data=appointment_data
        )
        
        return result is not None
    
    def update_appointment_status(
        self, 
        appointment_id: int, 
        status: str
    ) -> bool:
        """به‌روزرسانی وضعیت نوبت در CRM"""
        if not self.config.is_configured():
            return False
        
        result = self._make_request(
            method="PATCH",
            endpoint=f"{self.config.endpoints['appointments']}/{appointment_id}",
            data={"status": status}
        )
        
        return result is not None
    
    def get_patients_from_crm(self, limit: int = 100) -> Optional[List[Dict]]:
        """دریافت لیست بیماران از CRM"""
        if not self.config.is_configured():
            return None
        
        result = self._make_request(
            method="GET",
            endpoint=self.config.endpoints["patients"],
            params={"limit": limit}
        )
        
        return result.get("data") if result else None
    
    def get_appointments_from_crm(
        self, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional[List[Dict]]:
        """دریافت لیست نوبت‌ها از CRM"""
        if not self.config.is_configured():
            return None
        
        params = {}
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()
        
        result = self._make_request(
            method="GET",
            endpoint=self.config.endpoints["appointments"],
            params=params
        )
        
        return result.get("data") if result else None
    
    def _convert_patient_to_crm_format(self, patient: Patient) -> Dict:
        """تبدیل Patient به فرمت مورد نیاز CRM"""
        return {
            "id": patient.id,
            "name": patient.name,
            "phone": patient.phone,
            "national_id": patient.national_id,
            "payment_type": patient.payment_type.value if patient.payment_type else None,
            "first_visit_date": patient.first_visit_date.isoformat() if patient.first_visit_date else None,
            "created_at": patient.created_at.isoformat() if patient.created_at else None,
            "updated_at": patient.updated_at.isoformat() if patient.updated_at else None
        }
    
    def _convert_appointment_to_crm_format(self, appointment: Appointment) -> Dict:
        """تبدیل Appointment به فرمت مورد نیاز CRM"""
        return {
            "id": appointment.id,
            "patient_id": appointment.patient_id,
            "appointment_date": appointment.appointment_date.isoformat() if appointment.appointment_date else None,
            "duration_minutes": appointment.duration_minutes,
            "payment_type": appointment.payment_type.value if appointment.payment_type else None,
            "treatment_type": appointment.treatment_type.value if appointment.treatment_type else None,
            "priority_score": appointment.priority_score,
            "ai_priority_score": appointment.ai_priority_score,
            "status": appointment.status,
            "notes": appointment.notes,
            "created_at": appointment.created_at.isoformat() if appointment.created_at else None,
            "updated_at": appointment.updated_at.isoformat() if appointment.updated_at else None
        }
    
    def sync_all_patients(self, db: Session, limit: int = 100) -> Dict[str, Any]:
        """همگام‌سازی تمام بیماران با CRM"""
        if not self.config.is_configured():
            return {
                "success": False,
                "message": "CRM is not configured or not enabled",
                "synced": 0,
                "failed": 0
            }
        
        patients = db.query(Patient).limit(limit).all()
        synced = 0
        failed = 0
        
        for patient in patients:
            try:
                if self.sync_patient(patient):
                    synced += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Error syncing patient {patient.id}: {e}")
                failed += 1
        
        return {
            "success": True,
            "message": f"Synced {synced} patients, {failed} failed",
            "synced": synced,
            "failed": failed,
            "total": len(patients)
        }
    
    def sync_all_appointments(
        self, 
        db: Session, 
        limit: int = 100,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """همگام‌سازی تمام نوبت‌ها با CRM"""
        if not self.config.is_configured():
            return {
                "success": False,
                "message": "CRM is not configured or not enabled",
                "synced": 0,
                "failed": 0
            }
        
        query = db.query(Appointment)
        if status:
            query = query.filter(Appointment.status == status)
        
        appointments = query.limit(limit).all()
        synced = 0
        failed = 0
        
        for appointment in appointments:
            try:
                if self.sync_appointment(appointment):
                    synced += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Error syncing appointment {appointment.id}: {e}")
                failed += 1
        
        return {
            "success": True,
            "message": f"Synced {synced} appointments, {failed} failed",
            "synced": synced,
            "failed": failed,
            "total": len(appointments)
        }


# نمونه سراسری برای استفاده در سراسر برنامه
crm_integration = CRMIntegration()





