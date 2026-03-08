"""
Slot Allocator (TVS v2)
========================
Recommends top N slots ranked by Final Score with full decision trace.
"""
import logging
from typing import List, Dict, Any, Optional

from app.engine.tvs.types import RecommendationV2, DecisionTrace
from app.engine.tvs.patient_value import compute_patient_tvs
from app.engine.tvs.slot_fit import compute_slot_fit
from app.engine.tvs.final_score import compute_final_score
from app.engine.scoring import DataStore

logger = logging.getLogger(__name__)


def recommend_slots_v2(
    slots: List[Dict[str, Any]],
    request_params: Dict[str, Any],
    data_store: DataStore,
    top_k: int = 5,
    weights_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Recommend top K slots using v2 value-based scoring.
    
    Process:
    1. Compute patient TVS once (patient-level score)
    2. For each slot: compute slot fit score
    3. For each slot: compute final score = f(patient_tvs, slot_fit)
    4. Sort by final score descending
    5. Return top K with full decision trace
    
    Args:
        slots: List of slot dictionaries
        request_params: Request parameters with patient/service info
        data_store: Data store with CSV data
        top_k: Number of recommendations to return
        weights_config: Optional weights (tvs weights + final weights)
        
    Returns:
        Dictionary with:
        - recommendations: List of RecommendationV2 objects
        - meta: Metadata (engine_version, total_evaluated, etc.)
    """
    if not slots:
        logger.warning("No slots provided for v2 recommendation")
        return {
            'recommendations': [],
            'meta': {
                'engine_version': 'v2',
                'total_evaluated': 0,
                'top_k': top_k
            }
        }
    
    # Extract weights
    if weights_config is None:
        weights_config = {}
    
    tvs_weights = weights_config.get('tvs', {})
    final_weights = weights_config.get('final', {})
    
    patient_weight = final_weights.get('patient_weight', 0.70)
    slot_weight = final_weights.get('slot_weight', 0.30)
    
    logger.info(f"Starting v2 recommendation for {len(slots)} slots (top_k={top_k})")
    
    # Step 1: Get service info (accepts service_id or service_name)
    service_lookup_key = request_params.get('service_id') or request_params.get('service_name')
    service_info = None
    if service_lookup_key:
        service_info = data_store.get_service_info(service_lookup_key)
        if service_info:
            logger.debug(f"Found service info for '{service_lookup_key}'")
        else:
            logger.warning(f"Service '{service_lookup_key}' not found in catalog")
    
    # Step 2: Compute patient TVS (once per request)
    logger.debug("Computing patient TVS...")
    patient_value_result = compute_patient_tvs(
        request_params=request_params,
        service_info=service_info,
        data_store=data_store,
        weights_config=tvs_weights
    )
    
    patient_tvs = patient_value_result.patient_tvs
    logger.info(f"Patient TVS={patient_tvs:.3f}")
    
    # Step 3: Score each slot
    scored_recommendations = []
    
    for slot in slots:
        try:
            # Compute slot fit
            slot_fit_result = compute_slot_fit(
                slot=slot,
                service_info=service_info,
                request_params=request_params,
                data_store=data_store
            )
            
            # Compute final score
            final_score_result = compute_final_score(
                patient_tvs=patient_tvs,
                slot_fit_score=slot_fit_result.slot_fit_score,
                mode="weighted",
                patient_weight=patient_weight,
                slot_weight=slot_weight
            )
            
            # Build decision trace
            trace = DecisionTrace(
                # Patient value components
                cis=patient_value_result.cis,
                cis_notes=patient_value_result.trace.get('cis_notes', ''),
                ltvs=patient_value_result.ltvs,
                ltvs_notes=patient_value_result.trace.get('ltvs_notes', ''),
                risk=patient_value_result.risk,
                risk_notes=patient_value_result.trace.get('risk_notes', ''),
                fair=patient_value_result.fair,
                fair_notes=patient_value_result.trace.get('fair_notes', ''),
                urg=patient_value_result.urg,
                urg_notes=patient_value_result.trace.get('urg_notes', ''),
                patient_tvs=patient_tvs,
                # Slot fit components
                slot_fit_score=slot_fit_result.slot_fit_score,
                slot_urgency=slot_fit_result.urgency_score,
                slot_financial=slot_fit_result.financial_score,
                slot_availability=slot_fit_result.availability_score,
                slot_complexity_fit=slot_fit_result.complexity_fit_score,
                # Final score
                final_score=final_score_result.final_score,
                patient_weight=patient_weight,
                slot_weight=slot_weight,
                engine_version="v2"
            )
            
            # Create recommendation
            recommendation = RecommendationV2(
                slot=slot,
                final_score=final_score_result.final_score,
                patient_tvs=patient_tvs,
                slot_fit_score=slot_fit_result.slot_fit_score,
                trace=trace
            )
            
            scored_recommendations.append(recommendation)
            
        except Exception as e:
            logger.error(f"Error scoring slot {slot}: {e}", exc_info=True)
            continue
    
    # Step 4: Sort by final score descending
    scored_recommendations.sort(key=lambda r: r.final_score, reverse=True)
    
    # Step 5: Assign ranks and take top K
    top_recommendations = scored_recommendations[:top_k]
    for rank, rec in enumerate(top_recommendations, start=1):
        rec.rank = rank
    
    logger.info(f"V2 recommendation complete: {len(top_recommendations)} slots selected "
                f"(evaluated {len(scored_recommendations)} total)")
    
    # Build response
    return {
        'recommendations': top_recommendations,
        'meta': {
            'engine_version': 'v2',
            'total_evaluated': len(slots),
            'total_scored': len(scored_recommendations),
            'top_k': top_k,
            'patient_tvs': patient_tvs,
            'weights': {
                'tvs': tvs_weights,
                'final': {
                    'patient_weight': patient_weight,
                    'slot_weight': slot_weight
                }
            }
        }
    }
