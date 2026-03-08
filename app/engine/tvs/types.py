"""
Type definitions for Decision Engine v2 (TVS)
==============================================
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class PatientValueResult:
    """Result of patient value computation."""
    patient_tvs: float  # Total Value Score in [0, 1]
    
    # Components (all in [0, 1])
    cis: float  # Cash Impact Score
    ltvs: float  # Lifetime Value Score
    risk: float  # Risk Score (negative impact)
    fair: float  # Fairness Score (queue/waiting days)
    urg: float  # Urgency Score
    
    # Trace/notes for explainability
    trace: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate all scores are in [0, 1]."""
        for field_name in ['patient_tvs', 'cis', 'ltvs', 'risk', 'fair', 'urg']:
            value = getattr(self, field_name)
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"{field_name} must be in [0, 1], got {value}")


@dataclass
class SlotFitResult:
    """Result of slot fit computation (wrapper around v1 scoring)."""
    slot_fit_score: float  # Normalized score in [0, 1]
    
    # Breakdown from v1 scoring
    urgency_score: float
    financial_score: float
    availability_score: float
    complexity_fit_score: float
    
    # Original slot info
    slot: Dict[str, Any]
    
    # Trace/notes
    trace: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate slot_fit_score is in [0, 1]."""
        if not (0.0 <= self.slot_fit_score <= 1.0):
            raise ValueError(f"slot_fit_score must be in [0, 1], got {self.slot_fit_score}")


@dataclass
class FinalScoreResult:
    """Result of final score computation."""
    final_score: float  # Combined score in [0, 1]
    patient_tvs: float
    slot_fit_score: float
    
    # Weights used
    patient_weight: float
    slot_weight: float
    
    # Trace
    trace: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate final_score is in [0, 1]."""
        if not (0.0 <= self.final_score <= 1.0):
            raise ValueError(f"final_score must be in [0, 1], got {self.final_score}")


@dataclass
class DecisionTrace:
    """Detailed trace for explainability."""
    # Patient value components
    cis: float
    cis_notes: str
    
    ltvs: float
    ltvs_notes: str
    
    risk: float
    risk_notes: str
    
    fair: float
    fair_notes: str
    
    urg: float
    urg_notes: str
    
    patient_tvs: float
    
    # Slot fit components
    slot_fit_score: float
    slot_urgency: float
    slot_financial: float
    slot_availability: float
    slot_complexity_fit: float
    
    # Final score
    final_score: float
    patient_weight: float
    slot_weight: float
    
    # Additional metadata
    engine_version: str = "v2"


@dataclass
class RecommendationV2:
    """A single v2 recommendation with full trace."""
    # Slot info
    slot: Dict[str, Any]
    
    # Scores
    final_score: float
    patient_tvs: float
    slot_fit_score: float
    
    # Full trace
    trace: DecisionTrace
    
    # Metadata
    rank: int = 0  # Position in ranking (1-indexed)
