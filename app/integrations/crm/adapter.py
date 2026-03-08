"""CRM Adapter - bridges CRM data to scheduling engine context."""
import logging
from typing import Optional

from app.schemas.scheduling import PatientContext, SchedulingRequest, CaseContext
from app.integrations.crm.client import CRMClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def build_case_context_from_crm(
    crm_client: CRMClient,
    patient_id: str | int,
    service_name: str,
    desired_weekday: Optional[str] = None,
    preferred_doctor: Optional[str] = None,
    slot_minutes: int = 30
) -> CaseContext:
    """
    Build a CaseContext from CRM data.
    
    This adapter fetches all relevant patient information from the CRM
    and constructs a normalized CaseContext object that the engine can process.
    
    Args:
        crm_client: CRM client instance
        patient_id: Patient identifier
        service_name: Service/treatment name
        desired_weekday: Optional desired weekday override
        preferred_doctor: Optional preferred doctor override
        slot_minutes: Slot duration in minutes
        
    Returns:
        CaseContext with patient and request information
        
    Raises:
        ValueError: If patient not found or required data missing
    """
    logger.info(f"Building case context for patient {patient_id}")
    
    try:
        # Fetch patient basic info
        patient_data = crm_client.get_patient(patient_id)
        logger.debug(f"Fetched patient data: {patient_data.get('full_name')}")
        
        # Fetch insurance
        insurance_name = crm_client.get_patient_insurance(patient_id)
        logger.debug(f"Patient insurance: {insurance_name}")
        
        # Fetch unfinished treatments
        unfinished = crm_client.get_patient_unfinished(patient_id)
        unfinished_title = None
        if unfinished:
            # Take the most urgent or first unfinished treatment
            unfinished = sorted(unfinished, key=lambda x: {
                'high': 0, 'medium': 1, 'low': 2
            }.get(x.get('urgency', 'low'), 3))
            unfinished_title = unfinished[0].get('title')
            logger.debug(f"Unfinished treatment: {unfinished_title}")
        
        # Fetch preferences
        preferences = crm_client.get_patient_preferences(patient_id)
        pref_doctor = preferences.get('preferred_doctor')
        pref_weekdays = preferences.get('preferred_weekdays', [])
        pref_weekday = pref_weekdays[0] if pref_weekdays else None
        
        # Override with provided parameters
        if preferred_doctor:
            pref_doctor = preferred_doctor
        if desired_weekday:
            pref_weekday = desired_weekday
        
        # Fetch payment behavior
        payment_behavior = crm_client.get_payment_behavior(patient_id)
        
        # Build PatientContext
        patient_context = PatientContext(
            patient_id=patient_data['patient_id'],
            full_name=patient_data.get('full_name'),
            phone=patient_data.get('phone'),
            insurance_name=insurance_name,
            payment_behavior_tag=payment_behavior,
            unfinished_treatment_title=unfinished_title,
            preferred_doctor=pref_doctor,
            preferred_weekday=pref_weekday,
            notes=patient_data.get('notes')
        )
        
        # Build SchedulingRequest
        request = SchedulingRequest(
            service_name=service_name,
            desired_weekday=pref_weekday,
            preferred_doctor=pref_doctor,
            slot_minutes=slot_minutes
        )
        
        # Combine into CaseContext
        case_context = CaseContext(
            patient=patient_context,
            request=request
        )
        
        logger.info(f"Built case context for {patient_context.full_name}")
        return case_context
        
    except Exception as e:
        logger.error(f"Error building case context: {e}")
        raise


def extract_request_params(case_context: CaseContext) -> dict:
    """
    Extract request parameters from CaseContext for engine compatibility.
    
    This helper extracts the relevant fields from CaseContext and formats them
    for use with the existing scoring/recommendation engine.
    
    Args:
        case_context: Complete case context
        
    Returns:
        Dictionary with request parameters
    """
    return {
        'service_name': case_context.request.service_name,
        'service_id': getattr(case_context.request, 'service_id', None),
        'insurance_name': case_context.patient.insurance_name,
        'backlog_title': case_context.patient.unfinished_treatment_title,
        'preferred_doctor': (
            case_context.request.preferred_doctor or 
            case_context.patient.preferred_doctor
        ),
        'preferred_doctor_id': getattr(case_context.request, 'preferred_doctor_id', None),
        'preferred_weekday': (
            case_context.request.desired_weekday or 
            case_context.patient.preferred_weekday
        )
    }
