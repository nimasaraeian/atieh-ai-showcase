"""
Final Score Computation (TVS v2)
=================================
Combines Patient TVS with Slot Fit Score to produce final ranking score.
"""
import logging
from typing import Optional

from app.engine.tvs.types import FinalScoreResult

logger = logging.getLogger(__name__)


def clamp01(value: float) -> float:
    """Clamp value to [0, 1] range."""
    return max(0.0, min(1.0, value))


def compute_final_score(
    patient_tvs: float,
    slot_fit_score: float,
    mode: str = "weighted",
    patient_weight: Optional[float] = None,
    slot_weight: Optional[float] = None
) -> FinalScoreResult:
    """
    Compute final score by combining patient TVS and slot fit score.
    
    Modes:
    - "weighted" (default): final = patient_weight * patient_tvs + slot_weight * slot_fit_score
    - "multiplicative": final = patient_tvs * slot_fit_score
    
    Default weights for weighted mode:
    - patient_weight: 0.70
    - slot_weight: 0.30
    
    Args:
        patient_tvs: Patient Total Value Score [0, 1]
        slot_fit_score: Slot Fit Score [0, 1]
        mode: Combination mode ("weighted" or "multiplicative")
        patient_weight: Weight for patient TVS (weighted mode only)
        slot_weight: Weight for slot fit (weighted mode only)
        
    Returns:
        FinalScoreResult with combined score and trace
    """
    # Validate inputs
    if not (0.0 <= patient_tvs <= 1.0):
        raise ValueError(f"patient_tvs must be in [0, 1], got {patient_tvs}")
    if not (0.0 <= slot_fit_score <= 1.0):
        raise ValueError(f"slot_fit_score must be in [0, 1], got {slot_fit_score}")
    
    # Default weights
    if patient_weight is None:
        patient_weight = 0.70
    if slot_weight is None:
        slot_weight = 0.30
    
    # Compute final score based on mode
    if mode == "weighted":
        final_score = patient_weight * patient_tvs + slot_weight * slot_fit_score
        formula = f"final = {patient_weight}*patient_tvs + {slot_weight}*slot_fit"
    elif mode == "multiplicative":
        final_score = patient_tvs * slot_fit_score
        formula = "final = patient_tvs * slot_fit"
    else:
        raise ValueError(f"Unknown mode: {mode}. Must be 'weighted' or 'multiplicative'")
    
    # Clamp to [0, 1]
    final_score = clamp01(final_score)
    
    logger.debug(f"Final score={final_score:.3f} (mode={mode}, "
                 f"patient_tvs={patient_tvs:.3f}, slot_fit={slot_fit_score:.3f})")
    
    # Build trace
    trace = {
        'mode': mode,
        'formula': formula,
        'patient_tvs': patient_tvs,
        'slot_fit_score': slot_fit_score,
        'patient_weight': patient_weight,
        'slot_weight': slot_weight
    }
    
    return FinalScoreResult(
        final_score=final_score,
        patient_tvs=patient_tvs,
        slot_fit_score=slot_fit_score,
        patient_weight=patient_weight,
        slot_weight=slot_weight,
        trace=trace
    )
