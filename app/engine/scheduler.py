"""Schedule draft builder - selects best slot from recommendations."""
import logging
from typing import TYPE_CHECKING, List, Optional
from pathlib import Path

from app.schemas.scheduling import SchedulingRequest, SlotRecommendation, ScheduleDraft

if TYPE_CHECKING:
    from app.engine.scoring import DataStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def build_schedule_draft(
    recommendations: List[SlotRecommendation],
    request: SchedulingRequest,
    data_store: Optional["DataStore"] = None,
) -> Optional[ScheduleDraft]:
    """
    Build a schedule draft by selecting the best slot from recommendations.
    
    Strategy:
    1. If request.preferred_doctor_id or request.preferred_doctor is provided AND
       at least 1 recommendation has preferred_doctor_match=True, restrict candidates
       to only those matched rows. Otherwise use all recommendations.
    2. Select the top scoring slot from candidates (same scoring rule as before).
    3. Generate reason for the choice
    
    NOTE: This function NEVER returns empty. If preferred doctor matches exist,
    we restrict selection to those; otherwise we fall back to all recommendations.
    
    Args:
        recommendations: List of slot recommendations (sorted by score)
        request: Original scheduling request
        
    Returns:
        ScheduleDraft with chosen slot and reason, or None if no recommendations
    """
    if not recommendations:
        logger.warning("No recommendations available to build draft")
        return None
    
    # 1) Restrict to preferred_doctor_match rows when applicable
    has_preferred = (
        getattr(request, "preferred_doctor_id", None) is not None
        or bool((request.preferred_doctor or "").strip())
    )
    matched = [r for r in recommendations if getattr(r, "preferred_doctor_match", False) is True]
    match_count = len(matched)
    
    if has_preferred and matched:
        candidates = matched
        restricted = True
        logger.info("Preferred doctor match count: %d; restricting selection to matched slots", match_count)
    else:
        candidates = recommendations
        restricted = False
        if match_count > 0:
            logger.info("Preferred doctor match count: %d (no preferred doctor requested)", match_count)
        elif has_preferred:
            logger.info("Preferred doctor match count: 0; using all %d recommendations", len(recommendations))
            logger.warning("⚠️  Preferred doctor not available in %d recommendations", len(recommendations))
            # Log unique available doctors (up to 5)
            seen = set()
            unique_doctors = []
            for rec in recommendations:
                name = getattr(rec, "doctor", None)
                if not name or name in seen:
                    continue
                seen.add(name)
                unique_doctors.append(name)
                if len(unique_doctors) >= 5:
                    break
            logger.warning("📋 Available doctors: %r", unique_doctors)
            logger.warning("✅ Falling back to all recommendations (boost mode)")
    # 2) Select the top scoring slot from candidates
    # NOTE: The score here is the FINAL score from recommender (including any boosts)
    best_slot = max(candidates, key=lambda r: float(r.score))
    
    # Log the selected slot with its score
    logger.info(f"📌 Selected slot: {best_slot.weekday} {best_slot.shift_code} "
                f"{best_slot.start_time}-{best_slot.end_time}, "
                f"doctor: {best_slot.doctor}, score: {best_slot.score:.3f}")
    
    # Generate reason
    reason = _generate_reason(
        best_slot,
        request,
        len(recommendations),
        len(candidates),
        restricted
    )
    
    # Create draft
    draft = ScheduleDraft(
        chosen_weekday=best_slot.weekday,
        shift_code=best_slot.shift_code,
        start_time=best_slot.start_time,
        end_time=best_slot.end_time,
        doctor=best_slot.doctor,
        score=best_slot.score,  # Use the SAME score from recommendation (no re-scoring)
        reason=reason
    )
    
    logger.info(f"Created schedule draft: {best_slot.weekday} {best_slot.shift_code} "
                f"{best_slot.start_time} with {best_slot.doctor} (score: {best_slot.score:.3f})")
    
    return draft


def _generate_reason(
    slot: SlotRecommendation,
    request: SchedulingRequest,
    total_recommendations: int,
    filtered_count: int,
    preferred_doctor_found: bool
) -> str:
    """
    Generate a human-readable reason for choosing this slot.
    
    Args:
        slot: Selected slot
        request: Original request
        total_recommendations: Total number of recommendations
        filtered_count: Number of candidates considered
        preferred_doctor_found: Whether we restricted to preferred doctor slots (matched and selected from them)
        
    Returns:
        Reason string
    """
    reasons = []
    
    # Primary reason: score
    if slot.score >= 0.8:
        reasons.append(f"Excellent match (score: {slot.score:.2f})")
    elif slot.score >= 0.6:
        reasons.append(f"Good match (score: {slot.score:.2f})")
    else:
        reasons.append(f"Best available (score: {slot.score:.2f})")
    
    # Preferred doctor status - only when user requested a preferred doctor (by id or name)
    has_pref = (request.preferred_doctor or "").strip() or getattr(request, "preferred_doctor_id", None) is not None
    if has_pref:
        if preferred_doctor_found:
            reasons.append("✅ preferred doctor available")
        else:
            reasons.append(f"⚠️  preferred doctor not available, selected best from {total_recommendations} options")
    
    # High availability
    if slot.breakdown.availability_score >= 1.0:
        reasons.append("doctor confirmed available")
    
    # Strong factors
    if slot.breakdown.urgency_score >= 0.8:
        reasons.append("high urgency treatment")
    
    if slot.breakdown.financial_score >= 0.8:
        reasons.append("priority insurance")
    
    # Shift timing
    shift_names = {'D': 'morning', 'E': 'evening', 'N': 'night'}
    shift_name = shift_names.get(slot.shift_code, slot.shift_code)
    reasons.append(f"{shift_name} shift")
    
    # Complexity consideration
    if slot.service_complexity > 0.8 and slot.shift_code != 'N':
        reasons.append("complex procedure scheduled in optimal shift")
    
    return "; ".join(reasons)


def save_draft_to_csv(draft: ScheduleDraft, output_path: str):
    """
    Save schedule draft to CSV file.
    
    Args:
        draft: Schedule draft to save
        output_path: Path to output CSV file
    """
    import csv
    
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow([
            'chosen_weekday', 'shift_code', 'start_time', 'end_time',
            'doctor', 'score', 'reason'
        ])
        
        # Write draft
        writer.writerow([
            draft.chosen_weekday,
            draft.shift_code,
            draft.start_time,
            draft.end_time,
            draft.doctor,
            f"{draft.score:.3f}",
            draft.reason
        ])
    
    logger.info(f"Saved schedule draft to {output_path}")


def build_and_save_draft(
    recommendations: List[SlotRecommendation],
    request: SchedulingRequest,
    output_path: str = "data/outputs/schedule_draft.csv"
) -> Optional[ScheduleDraft]:
    """
    Build schedule draft and save to CSV in one step.
    
    Args:
        recommendations: List of slot recommendations
        request: Original scheduling request
        output_path: Path to output CSV file
        
    Returns:
        ScheduleDraft or None
    """
    draft = build_schedule_draft(recommendations, request)
    
    if draft:
        save_draft_to_csv(draft, output_path)
    else:
        logger.warning("No draft created, CSV not saved")
    
    return draft
