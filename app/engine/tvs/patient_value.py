"""
Patient Value Computation (TVS v2)
===================================
Computes Patient Total Value Score (TVS) based on:
- CIS: Cash Impact Score (revenue potential)
- LTVS: Lifetime Value Score (patient history)
- RISK: Risk Score (no-show, late payment, debt)
- FAIR: Fairness Score (queue/waiting time)
- URG: Urgency Score (medical urgency)

Formula: patient_tvs = clamp01(0.55*CIS + 0.35*LTVS - 0.25*RISK + 0.20*FAIR + 0.10*URG)
"""
import logging
import math
from typing import Dict, Any, Optional

from app.engine.tvs.types import PatientValueResult
from app.engine.scoring import DataStore, calculate_urgency_score
from app.utils.fa_normalize import normalize_fa

logger = logging.getLogger(__name__)


def clamp01(value: float) -> float:
    """Clamp value to [0, 1] range."""
    return max(0.0, min(1.0, value))


def log_normalize(value: float, scale: float = 1.0) -> float:
    """
    Normalize using log(1 + x) for money/count values.
    
    Args:
        value: Raw value (e.g., revenue in currency units)
        scale: Scaling factor to control normalization range
        
    Returns:
        Normalized value in [0, 1] (approximately)
    """
    if value <= 0:
        return 0.0
    normalized = math.log1p(value / scale) / math.log1p(100)  # log base chosen for reasonable range
    return clamp01(normalized)


def compute_cis(
    request_params: Dict[str, Any],
    service_info: Optional[Dict[str, Any]],
    data_store: DataStore
) -> tuple[float, str]:
    """
    Compute Cash Impact Score (CIS) in [0, 1].
    
    Factors:
    - Service price/revenue potential
    - Insurance priority score (from insurance_priority.csv)
    - Payment type (cash=1.0, insurance varies)
    - Collection probability heuristic
    
    Args:
        request_params: Request parameters (may include insurance_name, payment_type, etc.)
        service_info: Service information (may include price, complexity)
        data_store: Data store with insurance_priority
        
    Returns:
        (cis_score, notes_string)
    """
    notes = []
    score_components = []
    
    # 1. Service revenue potential (if available)
    service_price = None
    if service_info and 'price' in service_info:
        service_price = float(service_info['price'])
        # Normalize price using log scale (assume 10M Toman as high value)
        price_score = log_normalize(service_price, scale=10_000_000)
        score_components.append(price_score)
        notes.append(f"service_price={service_price:.0f} -> price_score={price_score:.3f}")
    else:
        notes.append("service_price=N/A")
    
    # 2. Insurance priority score
    insurance_name = request_params.get('insurance_name')
    if insurance_name and data_store.insurance_priority is not None and not data_store.insurance_priority.empty:
        insurance_norm = normalize_fa(insurance_name.lower())
        
        # Try to find matching insurance
        match_found = False
        for _, row in data_store.insurance_priority.iterrows():
            row_name = normalize_fa(str(row['insurance_name']).lower())
            if insurance_norm == row_name or insurance_norm in row_name or row_name in insurance_norm:
                insurance_priority = float(row['priority_score'])
                score_components.append(insurance_priority)
                notes.append(f"insurance_priority={insurance_priority:.3f} ({insurance_name})")
                match_found = True
                break
        
        if not match_found:
            # Default insurance priority
            score_components.append(0.5)
            notes.append(f"insurance_priority=0.5 (default, {insurance_name} not found)")
    else:
        # No insurance or cash patient
        notes.append("insurance=N/A (assume cash/high priority)")
        score_components.append(0.9)  # Cash patients have high collection probability
    
    # 3. Payment type mapping (if present)
    payment_type = request_params.get('payment_type', '').lower()
    if 'cash' in payment_type or 'نقد' in payment_type:
        payment_multiplier = 1.0
        notes.append("payment_type=cash -> multiplier=1.0")
    elif payment_type:
        payment_multiplier = 0.85  # Insurance has slightly lower collection rate
        notes.append(f"payment_type={payment_type} -> multiplier=0.85")
    else:
        payment_multiplier = 0.9  # Default conservative
        notes.append("payment_type=N/A -> multiplier=0.9")
    
    # 4. Compute CIS
    if score_components:
        base_cis = sum(score_components) / len(score_components)
    else:
        base_cis = 0.5  # Default if no info
        notes.append("no_revenue_info -> base_cis=0.5")
    
    # Apply payment multiplier and clamp
    cis = clamp01(base_cis * payment_multiplier)
    notes.append(f"CIS={cis:.3f}")
    
    return cis, " | ".join(notes)


def compute_ltvs(
    request_params: Dict[str, Any]
) -> tuple[float, str]:
    """
    Compute Lifetime Value Score (LTVS) in [0, 1].
    
    Factors:
    - Patient visit count (history)
    - Total revenue from patient
    - Adherence/completion rate
    - Cancellation rate
    
    Args:
        request_params: May include visit_count, total_revenue, adherence_rate, cancel_rate
        
    Returns:
        (ltvs_score, notes_string)
    """
    notes = []
    score_components = []
    
    # 1. Visit count (loyalty)
    visit_count = request_params.get('visit_count', 0)
    if visit_count > 0:
        # Normalize: 1 visit=0.2, 5 visits=0.5, 20+ visits=~0.9
        visit_score = log_normalize(visit_count, scale=10)
        score_components.append(visit_score)
        notes.append(f"visit_count={visit_count} -> visit_score={visit_score:.3f}")
    else:
        notes.append("visit_count=0 (new patient)")
    
    # 2. Total revenue
    total_revenue = request_params.get('total_revenue', 0)
    if total_revenue > 0:
        # Normalize: high revenue patients are valuable
        revenue_score = log_normalize(total_revenue, scale=50_000_000)  # 50M Toman scale
        score_components.append(revenue_score)
        notes.append(f"total_revenue={total_revenue:.0f} -> revenue_score={revenue_score:.3f}")
    else:
        notes.append("total_revenue=0")
    
    # 3. Adherence/completion rate
    adherence_rate = request_params.get('adherence_rate')
    if adherence_rate is not None:
        adherence_score = clamp01(float(adherence_rate))
        score_components.append(adherence_score)
        notes.append(f"adherence_rate={adherence_rate:.3f}")
    
    # 4. Cancellation rate (inverse)
    cancel_rate = request_params.get('cancel_rate')
    if cancel_rate is not None:
        cancel_penalty = clamp01(1.0 - float(cancel_rate))
        score_components.append(cancel_penalty)
        notes.append(f"cancel_rate={cancel_rate:.3f} -> penalty={cancel_penalty:.3f}")
    
    # Compute LTVS
    if score_components:
        ltvs = sum(score_components) / len(score_components)
        notes.append(f"LTVS={ltvs:.3f}")
    else:
        # Default for new patients with no history
        ltvs = 0.5
        notes.append("no_history -> LTVS=0.5 (default)")
    
    return clamp01(ltvs), " | ".join(notes)


def compute_risk(
    request_params: Dict[str, Any]
) -> tuple[float, str]:
    """
    Compute Risk Score in [0, 1].
    
    Higher risk = higher score (negative impact on TVS).
    
    Factors:
    - no_show_risk
    - late_payment_risk
    - open_debt flag
    
    Args:
        request_params: May include no_show_risk, late_payment_risk, has_open_debt
        
    Returns:
        (risk_score, notes_string)
    """
    notes = []
    risk_components = []
    
    # 1. No-show risk
    no_show_risk = request_params.get('no_show_risk')
    if no_show_risk is not None:
        no_show = clamp01(float(no_show_risk))
        risk_components.append(no_show)
        notes.append(f"no_show_risk={no_show:.3f}")
    
    # 2. Late payment risk
    late_payment_risk = request_params.get('late_payment_risk')
    if late_payment_risk is not None:
        late_pay = clamp01(float(late_payment_risk))
        risk_components.append(late_pay)
        notes.append(f"late_payment_risk={late_pay:.3f}")
    
    # 3. Open debt flag
    has_open_debt = request_params.get('has_open_debt', False)
    if has_open_debt:
        risk_components.append(0.6)  # Significant risk
        notes.append("has_open_debt=True -> +0.6")
    
    # Compute risk
    if risk_components:
        risk = sum(risk_components) / len(risk_components)
        notes.append(f"RISK={risk:.3f}")
    else:
        # Default conservative risk for unknown patients
        risk = 0.25
        notes.append("no_risk_info -> RISK=0.25 (conservative)")
    
    return clamp01(risk), " | ".join(notes)


def compute_fair(
    request_params: Dict[str, Any]
) -> tuple[float, str]:
    """
    Compute Fairness Score in [0, 1].
    
    Rewards patients who have been waiting longer.
    
    Factors:
    - queue_days or waiting_days
    
    Args:
        request_params: May include queue_days, waiting_days
        
    Returns:
        (fair_score, notes_string)
    """
    notes = []
    
    queue_days = request_params.get('queue_days') or request_params.get('waiting_days')
    
    if queue_days is not None and queue_days > 0:
        # Normalize: 1 day=0.1, 7 days=0.5, 30+ days=~0.9
        fair = log_normalize(queue_days, scale=20)
        notes.append(f"queue_days={queue_days} -> FAIR={fair:.3f}")
    else:
        # New request, minimal fairness bonus
        fair = 0.1
        notes.append("queue_days=N/A -> FAIR=0.1 (new request)")
    
    return clamp01(fair), " | ".join(notes)


def compute_urg(
    request_params: Dict[str, Any],
    data_store: DataStore
) -> tuple[float, str]:
    """
    Compute Urgency Score in [0, 1].
    
    Reuses existing calculate_urgency_score from v1.
    
    Args:
        request_params: Must include backlog_title
        data_store: Data store with unfinished_treatments
        
    Returns:
        (urg_score, notes_string)
    """
    backlog_title = request_params.get('backlog_title')
    
    if not backlog_title:
        notes = "backlog_title=N/A -> URG=0.5 (default)"
        return 0.5, notes
    
    # Use existing v1 urgency calculation
    urg = calculate_urgency_score(backlog_title, data_store.unfinished_treatments)
    notes = f"backlog_title='{backlog_title}' -> URG={urg:.3f}"
    
    return clamp01(urg), notes


def compute_patient_tvs(
    request_params: Dict[str, Any],
    service_info: Optional[Dict[str, Any]],
    data_store: DataStore,
    weights_config: Optional[Dict[str, float]] = None
) -> PatientValueResult:
    """
    Compute Patient Total Value Score (TVS).
    
    Formula: patient_tvs = clamp01(alpha*CIS + beta*LTVS - gamma*RISK + epsilon*FAIR + delta*URG)
    
    Default weights:
    - alpha: 0.55 (CIS)
    - beta: 0.35 (LTVS)
    - gamma: 0.25 (RISK, negative)
    - epsilon: 0.20 (FAIR)
    - delta: 0.10 (URG)
    
    Args:
        request_params: Request parameters with patient/service info
        service_info: Service catalog info
        data_store: Data store with CSV data
        weights_config: Optional custom weights (alpha, beta, gamma, epsilon, delta)
        
    Returns:
        PatientValueResult with TVS and all components
    """
    # Default weights
    if weights_config is None:
        weights_config = {}
    
    alpha = weights_config.get('alpha', 0.55)
    beta = weights_config.get('beta', 0.35)
    gamma = weights_config.get('gamma', 0.25)  # Note: applied as negative
    epsilon = weights_config.get('epsilon', 0.20)
    delta = weights_config.get('delta', 0.10)
    
    logger.debug(f"Computing patient TVS with weights: alpha={alpha}, beta={beta}, "
                 f"gamma={gamma}, epsilon={epsilon}, delta={delta}")
    
    # Compute components
    cis, cis_notes = compute_cis(request_params, service_info, data_store)
    ltvs, ltvs_notes = compute_ltvs(request_params)
    risk, risk_notes = compute_risk(request_params)
    fair, fair_notes = compute_fair(request_params)
    urg, urg_notes = compute_urg(request_params, data_store)
    
    # Compute patient TVS
    patient_tvs = clamp01(
        alpha * cis +
        beta * ltvs -
        gamma * risk +  # Note: negative impact
        epsilon * fair +
        delta * urg
    )
    
    logger.info(f"Patient TVS={patient_tvs:.3f} (CIS={cis:.3f}, LTVS={ltvs:.3f}, "
                f"RISK={risk:.3f}, FAIR={fair:.3f}, URG={urg:.3f})")
    
    # Build trace
    trace = {
        'cis_notes': cis_notes,
        'ltvs_notes': ltvs_notes,
        'risk_notes': risk_notes,
        'fair_notes': fair_notes,
        'urg_notes': urg_notes,
        'weights': {
            'alpha': alpha,
            'beta': beta,
            'gamma': gamma,
            'epsilon': epsilon,
            'delta': delta
        },
        'formula': f'TVS = {alpha}*CIS + {beta}*LTVS - {gamma}*RISK + {epsilon}*FAIR + {delta}*URG'
    }
    
    return PatientValueResult(
        patient_tvs=patient_tvs,
        cis=cis,
        ltvs=ltvs,
        risk=risk,
        fair=fair,
        urg=urg,
        trace=trace
    )
