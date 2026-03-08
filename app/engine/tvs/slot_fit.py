"""
Slot Fit Score Computation (TVS v2)
====================================
Wraps existing v1 score_slot() as SlotFitScore for v2 compatibility.
"""
import logging
from typing import Dict, Any, Optional

from app.engine.tvs.types import SlotFitResult
from app.engine.scoring import DataStore, score_slot

logger = logging.getLogger(__name__)


def compute_slot_fit(
    slot: Dict[str, Any],
    service_info: Optional[Dict[str, Any]],
    request_params: Dict[str, Any],
    data_store: DataStore
) -> SlotFitResult:
    """
    Compute Slot Fit Score by wrapping existing v1 score_slot().
    
    This maintains backward compatibility while providing v2 trace format.
    
    Args:
        slot: Slot dictionary with weekday, shift_code, start_time, end_time
        service_info: Service information from catalog
        request_params: Request parameters
        data_store: Data store with CSV data
        
    Returns:
        SlotFitResult with slot_fit_score and breakdown
    """
    # Call existing v1 scoring
    scored = score_slot(slot, service_info, request_params, data_store)
    
    # Extract components
    urgency_score = scored['urgency_score']
    financial_score = scored['financial_score']
    availability_score = scored['availability_score']
    complexity_fit_score = scored['complexity_fit_score']
    total_score = scored['total_score']  # This is already in [0, 1]
    
    # Build trace
    trace = {
        'v1_scoring': True,
        'urgency_score': urgency_score,
        'financial_score': financial_score,
        'availability_score': availability_score,
        'complexity_fit_score': complexity_fit_score,
        'v1_weights': {
            'urgency': 0.35,
            'financial': 0.30,
            'availability': 0.20,
            'complexity_fit': 0.15
        },
        'service_complexity': scored.get('service_complexity', 0.5)
    }
    
    logger.debug(f"Slot fit score={total_score:.3f} for {slot['weekday']} {slot['shift_code']}")
    
    return SlotFitResult(
        slot_fit_score=total_score,
        urgency_score=urgency_score,
        financial_score=financial_score,
        availability_score=availability_score,
        complexity_fit_score=complexity_fit_score,
        slot=slot,
        trace=trace
    )
