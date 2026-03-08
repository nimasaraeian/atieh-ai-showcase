"""CLI entry point for the scheduling engine."""
import sys
import os
import json
import logging
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from app.schemas.scheduling import SchedulingRequest, CaseContext
from app.engine.scoring import DataStore
from app.engine.recommender import recommend_slots, recommendations_to_csv
from app.engine.scheduler import build_and_save_draft
from app.integrations.crm.mock import MockCRMClient
from app.integrations.crm.adapter import build_case_context_from_crm
from pathlib import Path

def run_engine_job(*, service, insurance=None, backlog=None, doctor=None, weekday=None, out_dir="data/outputs"):
    """
    Run the scheduling engine and write outputs into the specified directory.
    Used by the API for per-request isolation; CLI uses run() which writes to data/outputs.
    """
    from app.schemas.scheduling import PatientContext

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = {"service_name": service}
    if insurance is not None:
        payload["insurance_name"] = insurance
    if backlog is not None:
        payload["backlog_title"] = backlog
    if doctor is not None:
        payload["preferred_doctor_id"] = doctor
    if weekday is not None:
        payload["preferred_weekday"] = weekday

    data_store = DataStore()
    data_store.load_from_csv()

    patient = PatientContext(
        patient_id="api",
        full_name=payload.get("patient_name", "Unknown"),
        insurance_name=payload.get("insurance_name"),
        unfinished_treatment_title=payload.get("backlog_title"),
        preferred_doctor=payload.get("preferred_doctor"),
        preferred_weekday=payload.get("preferred_weekday"),
    )
    request = SchedulingRequest(
        service_name=payload["service_name"],
        desired_weekday=payload.get("preferred_weekday"),
        preferred_doctor=payload.get("preferred_doctor"),
        preferred_doctor_id=payload.get("preferred_doctor_id"),
        slot_minutes=payload.get("slot_minutes", 30),
    )
    case_context = CaseContext(patient=patient, request=request)

    result = recommend_slots(case_context, data_store, top_n=200)

    rec_path = out_dir / "slot_recommendations.csv"
    draft_path = out_dir / "schedule_draft.csv"
    recommendations_to_csv(result.top_recommendations, str(rec_path))
    build_and_save_draft(result.top_recommendations, case_context.request, str(draft_path))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_case(case_context: CaseContext, data_store: DataStore = None) -> dict:
    """
    Run scheduling engine with a CaseContext (CRM-ready).
    
    Args:
        case_context: Complete case context with patient and request info
        data_store: Optional pre-loaded DataStore (will load if not provided)
        
    Returns:
        Dictionary with scheduling results
    """
    # Initialize data store if not provided
    if data_store is None:
        data_store = DataStore()
        data_store.load_from_csv()
    
    # Generate recommendations (temporarily use a larger top_n for diversity diagnostics)
    result = recommend_slots(case_context, data_store, top_n=200)
    
    # Save recommendations to CSV
    output_path = Path("data/outputs/slot_recommendations.csv")
    recommendations_to_csv(result.top_recommendations, str(output_path))
    
    # Build and save schedule draft
    draft_path = Path("data/outputs/schedule_draft.csv")
    # Use the request from case_context for draft building
    from app.schemas.scheduling import SchedulingRequest
    draft_request = SchedulingRequest(
        service_name=case_context.request.service_name,
        desired_weekday=case_context.request.desired_weekday or case_context.patient.preferred_weekday,
        preferred_doctor=case_context.request.preferred_doctor or case_context.patient.preferred_doctor,
        slot_minutes=case_context.request.slot_minutes
    )
    draft = build_and_save_draft(result.top_recommendations, draft_request, str(draft_path))
    
    # Convert to dict for output
    result_dict = {
        'success': True,
        'patient_id': case_context.patient.patient_id,
        'patient_name': case_context.patient.full_name,
        'total_recommendations': len(result.top_recommendations),
        'total_slots_evaluated': result.total_slots_evaluated,
        'generated_at': result.generated_at.isoformat(),
        'top_recommendations': [],
        'draft': None,
        'case_context': {
            'patient_id': case_context.patient.patient_id,
            'insurance': case_context.patient.insurance_name,
            'unfinished_treatment': case_context.patient.unfinished_treatment_title,
            'service_requested': case_context.request.service_name
        }
    }
    
    # Add recommendations
    for rec in result.top_recommendations:
        result_dict['top_recommendations'].append({
            'weekday': rec.weekday,
            'shift_code': rec.shift_code,
            'time': f"{rec.start_time}-{rec.end_time}",
            'doctor': rec.doctor,
            'score': round(rec.score, 3),
            'breakdown': {
                'urgency': round(rec.breakdown.urgency_score, 3),
                'financial': round(rec.breakdown.financial_score, 3),
                'availability': round(rec.breakdown.availability_score, 3),
                'complexity_fit': round(rec.breakdown.complexity_fit_score, 3)
            }
        })
    
    # Add draft
    if draft:
        result_dict['draft'] = {
            'weekday': draft.chosen_weekday,
            'shift_code': draft.shift_code,
            'time': f"{draft.start_time}-{draft.end_time}",
            'doctor': draft.doctor,
            'score': round(draft.score, 3),
            'reason': draft.reason
        }
    
    return result_dict


def run_from_crm(
    patient_id: str | int,
    service_name: str,
    desired_weekday: str = None,
    preferred_doctor: str = None,
    slot_minutes: int = 30,
    use_mock: bool = True
) -> dict:
    """
    Run scheduling engine by fetching patient data from CRM.
    
    Args:
        patient_id: Patient identifier in CRM
        service_name: Service/treatment name
        desired_weekday: Optional desired weekday
        preferred_doctor: Optional preferred doctor
        slot_minutes: Slot duration in minutes
        use_mock: If True, use MockCRMClient; otherwise use real CRM
        
    Returns:
        Dictionary with scheduling results
    """
    # Initialize CRM client
    if use_mock:
        crm_client = MockCRMClient()
        logger.info(f"Using MockCRMClient for patient {patient_id}")
    else:
        from app.integrations.crm.client import CRMClient
        crm_client = CRMClient()
        logger.info(f"Using real CRMClient for patient {patient_id}")
    
    # Build case context from CRM
    case_context = build_case_context_from_crm(
        crm_client=crm_client,
        patient_id=patient_id,
        service_name=service_name,
        desired_weekday=desired_weekday,
        preferred_doctor=preferred_doctor,
        slot_minutes=slot_minutes
    )
    
    # Run engine with case context
    return run_case(case_context)


def run(payload: dict) -> dict:
    """
    Run the scheduling engine with a request payload (legacy entry point).
    
    Args:
        payload: Dictionary with request parameters
        
    Returns:
        Dictionary with recommendation results and schedule draft
    """
    # Initialize data store
    data_store = DataStore()
    data_store.load_from_csv()
    
    # Build CaseContext from payload for proper handling
    from app.schemas.scheduling import PatientContext
    
    patient = PatientContext(
        patient_id="legacy",
        full_name=payload.get('patient_name', 'Unknown'),
        insurance_name=payload.get('insurance_name'),
        unfinished_treatment_title=payload.get('backlog_title'),
        preferred_doctor=payload.get('preferred_doctor'),
        preferred_weekday=payload.get('preferred_weekday')
    )
    
    request = SchedulingRequest(
        service_name=payload['service_name'],
        desired_weekday=payload.get('preferred_weekday'),
        preferred_doctor=payload.get('preferred_doctor'),
        preferred_doctor_id=payload.get('preferred_doctor_id'),
        slot_minutes=payload.get('slot_minutes', 30)
    )
    
    case_context = CaseContext(patient=patient, request=request)
    
    # Generate recommendations (temporarily use a larger top_n for diversity diagnostics)
    result = recommend_slots(case_context, data_store, top_n=200)
    
    # Save recommendations to CSV
    output_path = Path("data/outputs/slot_recommendations.csv")
    recommendations_to_csv(result.top_recommendations, str(output_path))
    
    # Build and save schedule draft
    draft_path = Path("data/outputs/schedule_draft.csv")
    draft = build_and_save_draft(result.top_recommendations, case_context.request, str(draft_path))
    
    # Convert to dict for output
    result_dict = {
        'success': True,
        'total_recommendations': len(result.top_recommendations),
        'total_slots_evaluated': result.total_slots_evaluated,
        'generated_at': result.generated_at.isoformat(),
        'top_recommendations': [],
        'draft': None
    }
    
    # Add recommendations
    for rec in result.top_recommendations:
        result_dict['top_recommendations'].append({
            'weekday': rec.weekday,
            'shift_code': rec.shift_code,
            'time': f"{rec.start_time}-{rec.end_time}",
            'doctor': rec.doctor,
            'score': round(rec.score, 3),
            'breakdown': {
                'urgency': round(rec.breakdown.urgency_score, 3),
                'financial': round(rec.breakdown.financial_score, 3),
                'availability': round(rec.breakdown.availability_score, 3),
                'complexity_fit': round(rec.breakdown.complexity_fit_score, 3)
            }
        })
    
    # Add draft
    if draft:
        result_dict['draft'] = {
            'weekday': draft.chosen_weekday,
            'shift_code': draft.shift_code,
            'time': f"{draft.start_time}-{draft.end_time}",
            'doctor': draft.doctor,
            'score': round(draft.score, 3),
            'reason': draft.reason
        }
    
    return result_dict


def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Atieh Scheduling Engine')
    parser.add_argument('--service', required=True, help='Service name')
    parser.add_argument('--insurance', help='Insurance name')
    parser.add_argument('--backlog', help='Backlog title')
    parser.add_argument('--doctor', help='Preferred doctor (name or id)')
    parser.add_argument('--weekday', help='Preferred weekday')
    parser.add_argument('--output', default='data/outputs/slot_recommendations.csv',
                       help='Output CSV path')
    
    args = parser.parse_args()
    
    # Build payload
    payload = {'service_name': args.service}
    if args.insurance:
        payload['insurance_name'] = args.insurance
    if args.backlog:
        payload['backlog_title'] = args.backlog
    raw = args.doctor.strip() if args.doctor else None
    preferred_doctor_id = int(raw) if raw and raw.isdigit() else None
    preferred_doctor_name = raw if raw and not raw.isdigit() else None

    logger.info(
        "Preferred doctor parsed: raw=%r id=%r name=%r",
        raw, preferred_doctor_id, preferred_doctor_name,
    )

    if preferred_doctor_name:
        payload['preferred_doctor'] = preferred_doctor_name
    if preferred_doctor_id is not None:
        payload['preferred_doctor_id'] = preferred_doctor_id
    if args.weekday:
        payload['preferred_weekday'] = args.weekday
    
    # Run engine
    result = run(payload)
    
    # Print results
    print("\n" + "="*80)
    print("SCHEDULING ENGINE RESULTS")
    print("="*80)
    print(f"Service: {args.service}")
    print(f"Total slots evaluated: {result['total_slots_evaluated']}")
    print(f"Top recommendations: {result['total_recommendations']}")
    print(f"Generated at: {result['generated_at']}")
    
    # Print draft
    if result.get('draft'):
        print("\n" + "="*80)
        print("SCHEDULE DRAFT (RECOMMENDED CHOICE)")
        print("="*80)
        draft = result['draft']
        print(f"Date: {draft['weekday']} - {draft['shift_code']} shift")
        print(f"Time: {draft['time']}")
        print(f"Doctor: {draft['doctor']}")
        print(f"Score: {draft['score']:.3f}")
        print(f"Reason: {draft['reason']}")
    
    print("\n" + "="*80)
    print("TOP 10 RECOMMENDATIONS")
    print("="*80)
    
    for idx, rec in enumerate(result['top_recommendations'], 1):
        print(f"\n{idx}. {rec['weekday']} - {rec['shift_code']} - {rec['time']}")
        print(f"   Doctor: {rec['doctor']}")
        print(f"   Score: {rec['score']:.3f}")
        print(f"   Breakdown: U={rec['breakdown']['urgency']:.2f} "
              f"F={rec['breakdown']['financial']:.2f} "
              f"A={rec['breakdown']['availability']:.2f} "
              f"C={rec['breakdown']['complexity_fit']:.2f}")
    
    print("\n" + "="*80)
    print(f"Recommendations saved to: {args.output}")
    print(f"Schedule draft saved to: data/outputs/schedule_draft.csv")
    print("="*80)


if __name__ == '__main__':
    main()
