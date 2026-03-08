"""
Decision Engine v2: Value-Based Scheduling (TVS)
=================================================
Total Value Scoring that combines Patient Total Value Score (TVS) 
with Slot Fit Score for optimal scheduling decisions.

Components:
- patient_value: Compute patient TVS (CIS + LTVS - RISK + FAIR + URG)
- slot_fit: Wrap existing slot scoring as SlotFitScore
- final_score: Combine patient_tvs and slot_fit_score
- allocator: Rank slots and return top N with decision trace
"""

from app.engine.tvs.types import (
    PatientValueResult,
    SlotFitResult,
    FinalScoreResult,
    RecommendationV2,
    DecisionTrace
)
from app.engine.tvs.patient_value import compute_patient_tvs
from app.engine.tvs.slot_fit import compute_slot_fit
from app.engine.tvs.final_score import compute_final_score
from app.engine.tvs.allocator import recommend_slots_v2

__all__ = [
    'PatientValueResult',
    'SlotFitResult',
    'FinalScoreResult',
    'RecommendationV2',
    'DecisionTrace',
    'compute_patient_tvs',
    'compute_slot_fit',
    'compute_final_score',
    'recommend_slots_v2',
]
