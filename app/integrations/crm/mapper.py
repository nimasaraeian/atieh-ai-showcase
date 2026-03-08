"""
CRM Data Mapper
===============
Maps CRM dictionaries to canonical internal models.
Handles field name differences, format conversions, and data normalization.
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.schemas.canonical import (
    PatientCore,
    AppointmentCore,
    PaymentCore,
    DoctorCore,
    ScheduleCore,
    BlockCore,
    PatientHistoryCore
)

logger = logging.getLogger(__name__)

# Mapping tables for status/type conversions
STATUS_MAPPING = {
    # CRM status -> internal status
    'booked': 'pending',
    'confirmed': 'confirmed',
    'completed': 'completed',
    'cancelled': 'cancelled',
    'no_show': 'cancelled',
    'rescheduled': 'rescheduled',
    # Support internal statuses too
    'pending': 'pending',
}

PAYMENT_STATUS_MAPPING = {
    'paid': 'paid',
    'partial': 'partial',
    'pending': 'pending',
    'refunded': 'refunded',
}

PAYMENT_TYPE_MAPPING = {
    'cash': 'cash',
    'نقدی': 'cash',
    # Insurance mappings
    **{f'insurance_{i}': f'insurance_{i}' for i in range(1, 21)},
    **{f'بیمه_{i}': f'insurance_{i}' for i in range(1, 21)},
}


def normalize_payment_type(payment_type: str) -> str:
    """Normalize payment type to standard format."""
    pt_lower = payment_type.lower().strip()
    return PAYMENT_TYPE_MAPPING.get(pt_lower, payment_type)


def normalize_status(status: str) -> str:
    """Normalize status to standard format."""
    st_lower = status.lower().strip()
    return STATUS_MAPPING.get(st_lower, status)


def normalize_payment_status(status: str) -> str:
    """Normalize payment status to standard format."""
    st_lower = status.lower().strip()
    return PAYMENT_STATUS_MAPPING.get(st_lower, status)


def safe_datetime_parse(dt_str: Optional[str]) -> Optional[datetime]:
    """Safely parse datetime string."""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except Exception as e:
        logger.warning(f"Failed to parse datetime '{dt_str}': {e}")
        return None


def map_patient(crm_patient: Dict[str, Any]) -> PatientCore:
    """
    Map CRM patient dictionary to PatientCore model.
    
    Args:
        crm_patient: Raw patient data from CRM
        
    Returns:
        PatientCore instance
    """
    first_visit_date = safe_datetime_parse(crm_patient.get('first_visit_date')) or datetime.now()
    
    # Calculate lifetime days
    lifetime_days = 0
    if first_visit_date:
        lifetime_days = max(0, (datetime.now() - first_visit_date).days)
    
    return PatientCore(
        id=str(crm_patient['id']),
        name=crm_patient['name'],
        phone=crm_patient['phone'],
        national_id=crm_patient.get('national_id'),
        payment_type=normalize_payment_type(crm_patient.get('payment_type', 'cash')),
        first_visit_date=first_visit_date,
        lifetime_days=lifetime_days,
        notes=crm_patient.get('notes')
    )


def map_appointment(crm_appt: Dict[str, Any]) -> AppointmentCore:
    """
    Map CRM appointment dictionary to AppointmentCore model.
    
    Args:
        crm_appt: Raw appointment data from CRM
        
    Returns:
        AppointmentCore instance
    """
    appointment_date = safe_datetime_parse(crm_appt.get('appointment_date')) or datetime.now()
    
    return AppointmentCore(
        id=str(crm_appt['id']),
        patient_id=str(crm_appt['patient_id']),
        service_id=str(crm_appt.get('service_id', 'unknown')),
        service_name=crm_appt.get('service_name', 'Unknown Service'),
        appointment_date=appointment_date,
        duration_minutes=crm_appt.get('duration_minutes', 30),
        payment_type=normalize_payment_type(crm_appt.get('payment_type', 'cash')),
        status=normalize_status(crm_appt.get('status', 'pending')),
        priority_score=crm_appt.get('priority_score', 0.0),
        did_patient_show_up=crm_appt.get('did_patient_show_up'),
        cancellation_reason=crm_appt.get('cancellation_reason'),
        notes=crm_appt.get('notes')
    )


def map_payment(crm_payment: Dict[str, Any]) -> PaymentCore:
    """
    Map CRM payment dictionary to PaymentCore model.
    
    Args:
        crm_payment: Raw payment data from CRM
        
    Returns:
        PaymentCore instance
    """
    payment_date = safe_datetime_parse(crm_payment.get('payment_date'))
    
    return PaymentCore(
        id=str(crm_payment['id']),
        appointment_id=str(crm_payment['appointment_id']),
        patient_id=str(crm_payment['patient_id']),
        amount=float(crm_payment.get('amount', 0.0)),
        payment_type=normalize_payment_type(crm_payment.get('payment_type', 'cash')),
        payment_status=normalize_payment_status(crm_payment.get('payment_status', 'pending')),
        paid_on_time=crm_payment.get('paid_on_time'),
        payment_delay_days=crm_payment.get('payment_delay_days'),
        payment_date=payment_date
    )


def map_doctor(crm_doctor: Dict[str, Any]) -> DoctorCore:
    """
    Map CRM doctor dictionary to DoctorCore model.
    
    Args:
        crm_doctor: Raw doctor data from CRM
        
    Returns:
        DoctorCore instance
    """
    return DoctorCore(
        id=str(crm_doctor['id']),
        name=crm_doctor['name'],
        specialty=crm_doctor.get('specialty'),
        years_of_experience=crm_doctor.get('years_of_experience', 0),
        rating=float(crm_doctor.get('rating', 0.0)),
        is_active=crm_doctor.get('is_active', True)
    )


def map_schedule(crm_schedule: Dict[str, Any]) -> ScheduleCore:
    """
    Map CRM schedule dictionary to ScheduleCore model.
    
    Args:
        crm_schedule: Raw schedule data from CRM
        
    Returns:
        ScheduleCore instance
    """
    return ScheduleCore(
        id=str(crm_schedule['id']),
        doctor_id=str(crm_schedule['doctor_id']),
        doctor_name=crm_schedule.get('doctor_name', ''),
        date=crm_schedule['date'],
        shift_code=crm_schedule.get('shift_code', 'D'),
        shift_name=crm_schedule.get('shift_name', 'صبح'),
        start_time=crm_schedule.get('start_time', '08:00'),
        end_time=crm_schedule.get('end_time', '14:00'),
        is_available=crm_schedule.get('is_available', True)
    )


def map_block(crm_block: Dict[str, Any]) -> BlockCore:
    """
    Map CRM block dictionary to BlockCore model.
    
    Args:
        crm_block: Raw block data from CRM
        
    Returns:
        BlockCore instance
    """
    start_datetime = safe_datetime_parse(crm_block.get('start_datetime')) or datetime.now()
    end_datetime = safe_datetime_parse(crm_block.get('end_datetime')) or datetime.now()
    
    return BlockCore(
        id=str(crm_block['id']),
        doctor_id=str(crm_block['doctor_id']),
        doctor_name=crm_block.get('doctor_name', ''),
        block_type=crm_block.get('block_type', 'other'),
        block_name=crm_block.get('block_name', ''),
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        reason=crm_block.get('reason')
    )


def calculate_patient_history(
    patient: PatientCore,
    appointments: List[AppointmentCore],
    payments: List[PaymentCore]
) -> PatientHistoryCore:
    """
    Calculate patient history with statistics.
    
    Args:
        patient: Patient core data
        appointments: List of appointments
        payments: List of payments
        
    Returns:
        PatientHistoryCore with calculated stats
    """
    total = len(appointments)
    completed = sum(1 for a in appointments if a.status == 'completed')
    cancelled = sum(1 for a in appointments if a.status == 'cancelled')
    no_show = sum(1 for a in appointments if a.did_patient_show_up is False)
    
    # Late payments
    late_payment_count = sum(1 for p in payments if p.paid_on_time is False)
    
    # Rates
    completion_rate = completed / total if total > 0 else 0.0
    payment_reliability = 1.0 - (late_payment_count / len(payments)) if payments else 1.0
    
    return PatientHistoryCore(
        patient=patient,
        appointments=appointments,
        payments=payments,
        total_appointments=total,
        completed_appointments=completed,
        cancelled_appointments=cancelled,
        no_show_count=no_show,
        late_payment_count=late_payment_count,
        completion_rate=round(completion_rate, 2),
        payment_reliability=round(payment_reliability, 2)
    )


# Bulk mappers
def map_patients(crm_patients: List[Dict[str, Any]]) -> List[PatientCore]:
    """Map list of CRM patients to PatientCore list."""
    return [map_patient(p) for p in crm_patients]


def map_appointments(crm_appointments: List[Dict[str, Any]]) -> List[AppointmentCore]:
    """Map list of CRM appointments to AppointmentCore list."""
    return [map_appointment(a) for a in crm_appointments]


def map_payments(crm_payments: List[Dict[str, Any]]) -> List[PaymentCore]:
    """Map list of CRM payments to PaymentCore list."""
    return [map_payment(p) for p in crm_payments]


def map_doctors(crm_doctors: List[Dict[str, Any]]) -> List[DoctorCore]:
    """Map list of CRM doctors to DoctorCore list."""
    return [map_doctor(d) for d in crm_doctors]


def map_schedules(crm_schedules: List[Dict[str, Any]]) -> List[ScheduleCore]:
    """Map list of CRM schedules to ScheduleCore list."""
    return [map_schedule(s) for s in crm_schedules]


def map_blocks(crm_blocks: List[Dict[str, Any]]) -> List[BlockCore]:
    """Map list of CRM blocks to BlockCore list."""
    return [map_block(b) for b in crm_blocks]
