"""Main recommendation engine."""
import logging
import os
from typing import List, Union
import random

from app.schemas.scheduling import (
    SchedulingRequest, SchedulingResult, SlotRecommendation, ScoreBreakdown,
    CaseContext
)
from app.engine.time_blocks import generate_all_slots
from app.engine.scoring import DataStore, score_slot
from app.config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _build_reason_strings_fa(scored: dict) -> List[str]:
    """Build Persian explanation strings for a scored slot."""
    reasons = []
    u = scored.get('urgency_score', 0)
    f = scored.get('financial_score', 0)
    a = scored.get('availability_score', 0)
    c = scored.get('complexity_fit_score', 0)
    reasons.append(f"فوریت درمان: {u:.0%}")
    reasons.append(f"اولویت بیمه: {f:.0%}")
    reasons.append(f"امتیاز دسترسی پزشک: {a:.0%}")
    reasons.append(f"تطابق پیچیدگی شیفت: {c:.0%}")
    if scored.get('preferred_doctor_match'):
        reasons.append("تطابق با پزشک مورد نظر: بله")
    boost = scored.get("preferred_doctor_boost", 0.0)
    if boost and boost > 0:
        reasons.append(f"بوست پزشک مورد نظر: +{boost:.2f}")
    return reasons


def recommend_slots(
    request: Union[SchedulingRequest, CaseContext],
    data_store: DataStore,
    top_n: int = 10,
    slot_minutes: int = 30,
    engine_version: str = None
) -> SchedulingResult:
    """
    Generate slot recommendations based on request and scoring.
    
    Args:
        request: SchedulingRequest or CaseContext with patient info
        data_store: Loaded data store
        top_n: Number of top recommendations to return
        slot_minutes: Slot duration in minutes
        engine_version: "v1" or "v2" (if None, uses Config.ENGINE_VERSION or env var)
        
    Returns:
        SchedulingResult with top recommendations
    """
    # Determine engine version
    if engine_version is None:
        engine_version = os.environ.get('ENGINE_VERSION', Config.ENGINE_VERSION)
    
    logger.info(f"Using engine version: {engine_version}")
    
    # Route to appropriate engine
    if engine_version == "v2":
        return _recommend_slots_v2(request, data_store, top_n, slot_minutes)
    else:
        return _recommend_slots_v1(request, data_store, top_n, slot_minutes)


def _recommend_slots_v1(
    request: Union[SchedulingRequest, CaseContext],
    data_store: DataStore,
    top_n: int = 10,
    slot_minutes: int = 30
) -> SchedulingResult:
    """
    Generate slot recommendations based on request and scoring.
    
    Args:
        request: SchedulingRequest or CaseContext with patient info
        data_store: Loaded data store
        top_n: Number of top recommendations to return
        slot_minutes: Slot duration in minutes
        
    Returns:
        SchedulingResult with top recommendations
    """
    # Extract request parameters from CaseContext if needed
    if isinstance(request, CaseContext):
        from app.integrations.crm.adapter import extract_request_params
        request_params = extract_request_params(request)
        service_name = request.request.service_name
        preferred_weekday = request.request.desired_weekday or request.patient.preferred_weekday
        original_request = request.request
    else:
        # Legacy SchedulingRequest
        request_params = {
            'service_name': request.service_name,
            'service_id': getattr(request, 'service_id', None),
            'insurance_name': getattr(request, 'insurance_name', None),
            'backlog_title': getattr(request, 'backlog_title', None),
            'preferred_doctor': request.preferred_doctor,
            'preferred_weekday': getattr(request, 'preferred_weekday', None)
        }
        service_name = request.service_name
        preferred_weekday = request_params.get('preferred_weekday')
        original_request = request
    
    service_lookup_key = request_params.get("service_id") or service_name
    logger.info(f"Generating recommendations for service: {service_name} (lookup: {service_lookup_key})")
    
    # Get service information (accepts service_id or Persian service_name)
    service_info = data_store.get_service_info(service_lookup_key)
    if not service_info:
        logger.warning(f"Service not found in catalog: {service_lookup_key}")
        service_info = {
            'default_duration_min': getattr(original_request, 'slot_minutes', None) or slot_minutes or 30,
            'complexity_weight': 0.5
        }

    service_duration = service_info.get('default_duration_min', slot_minutes or 30)
    
    # Generate all possible slots
    all_slots = generate_all_slots(slot_minutes)
    logger.info(f"Generated {len(all_slots)} total slots")
    
    # Filter by preferred weekday if specified
    if preferred_weekday:
        from app.utils.fa_normalize import normalize_fa
        preferred_norm = normalize_fa(preferred_weekday)
        all_slots = [
            slot for slot in all_slots
            if normalize_fa(slot['weekday']) == preferred_norm
        ]
        logger.info(f"Filtered to {len(all_slots)} slots for preferred weekday")
    
    # Snapshot 1: ALL_SLOTS after weekday filter
    if all_slots:
        total_all = len(all_slots)
        unique_weekdays_all = len({s['weekday'] for s in all_slots})
        unique_shifts_all = len({s['shift_code'] for s in all_slots})
        sample_all = [
            (s['weekday'], s['start_time'], s['shift_code'], None, None)
            for s in all_slots[:30]
        ]
        logger.info(
            "ALL_SLOTS summary: total=%d, unique_weekdays=%d, unique_shifts=%d; sample=%r",
            total_all, unique_weekdays_all, unique_shifts_all, sample_all
        )
    
    # Resolve preferred_doctor to doctor_id for scoring
    preferred_doctor = request_params.get('preferred_doctor')
    if preferred_doctor:
        from app.engine.doctor_matcher import match_doctor
        pref_ref = match_doctor(preferred_doctor, getattr(data_store, "doctor_ref_by_norm", {}))
        preferred_doctor_id = pref_ref.doctor_id if pref_ref else None
        request_params["preferred_doctor_id"] = preferred_doctor_id
    else:
        preferred_doctor_id = None
        request_params["preferred_doctor_id"] = None

    scored_slots = []
    for slot in all_slots:
        scored = score_slot(slot, service_info, request_params, data_store)
        scored_slots.append(scored)

    # Log preferred doctor and boost stats
    if preferred_doctor:
        from app.utils.doctor_name import normalize_doctor_name
        from app.utils.log_sanitize import safe_norm_doctor
        from app.utils.text import find_best_doctor_match
        from app.config import Config

        preferred_norm = safe_norm_doctor(preferred_doctor)
        logger.info("Preferred doctor requested: %r (normalized: %r, ref_id: %s)", preferred_doctor, preferred_norm, preferred_doctor_id or 'N/A')
        logger.info(f"Preferred doctor mode: {Config.PREFERRED_DOCTOR_MODE}")
        
        boost_count = sum(1 for s in scored_slots if s.get('preferred_doctor_match'))
        all_doctor_names = set()
        weekday_doctors = {}
        for scored in scored_slots:
            slot = scored['slot']
            doctors = data_store.get_doctors_for_slot(slot['weekday'], slot['shift_code'])
            all_doctor_names.update(doctors)
            wd = slot['weekday']
            if wd not in weekday_doctors:
                weekday_doctors[wd] = set()
            weekday_doctors[wd].update(doctors)
        
        if boost_count == 0:
            # No matches found
            unique_doctors = sorted(list(all_doctor_names))
            if preferred_doctor_id:
                logger.warning(
                    "⚠️  Preferred doctor %r (ref_id: %s) found in reference but not in any of the %d shift slots",
                    preferred_doctor, preferred_doctor_id, len(scored_slots),
                )
            else:
                logger.warning(
                    "⚠️  Preferred doctor %r (normalized: %r) not found in reference or in any of the %d candidate slots",
                    preferred_doctor,
                    preferred_norm,
                    len(scored_slots),
                )
            
            if unique_doctors:
                logger.warning(f"📋 Available doctors across all shifts (total {len(unique_doctors)}):")
                # Show top 10 available doctors with normalized forms
                for i, doc in enumerate(unique_doctors[:10], 1):
                    doc_norm = safe_norm_doctor(doc)
                    logger.warning("   %s. %r (normalized: %r)", i, doc, doc_norm)
                
                if len(unique_doctors) > 10:
                    logger.warning(f"   ... and {len(unique_doctors) - 10} more doctors")
            
            # Log per-weekday breakdown if weekday was specified
            if preferred_weekday:
                logger.warning("📅 Doctors available on requested weekday %r:", preferred_weekday)
                if preferred_weekday in weekday_doctors:
                    weekday_docs = sorted(list(weekday_doctors[preferred_weekday]))
                    for i, doc in enumerate(weekday_docs[:5], 1):
                        doc_norm = safe_norm_doctor(doc)
                        logger.warning("   %s. %r (normalized: %r)", i, doc, doc_norm)
                    if len(weekday_docs) > 5:
                        logger.warning(f"   ... and {len(weekday_docs) - 5} more")
                else:
                    logger.warning("   (No slots found for weekday %r)", preferred_weekday)
            
            logger.warning(f"✅ Continuing with all {len(scored_slots)} slots (boost mode - no filtering)")
        else:
            logger.info(f"✅ Applied preferred doctor boost to {boost_count}/{len(scored_slots)} slots")
    
    # Sort by total score (descending)
    scored_slots.sort(key=lambda x: x['total_score'], reverse=True)
    
    # Snapshot 2: SCORED_SLOTS after sorting
    if scored_slots:
        total_scored = len(scored_slots)
        unique_weekdays_scored = len({s['slot']['weekday'] for s in scored_slots})
        unique_shifts_scored = len({s['slot']['shift_code'] for s in scored_slots})
        sample_scored = [
            (
                s['slot']['weekday'],
                s['slot']['start_time'],
                s['slot']['shift_code'],
                None,
                None,
            )
            for s in scored_slots[:30]
        ]
        logger.info(
            "SCORED_SLOTS summary: total=%d, unique_weekdays=%d, unique_shifts=%d; sample=%r",
            total_scored, unique_weekdays_scored, unique_shifts_scored, sample_scored
        )
    
    # Build recommendations
    from collections import defaultdict

    recommendations = []
    seen_combinations = set()
    doctor_counts: Dict[Optional[int], int] = defaultdict(int)
    max_per_doctor = max(5, int(top_n * 0.6))
    # Determine if we actually have multiple doctors across all scored slots
    all_doctor_ids: set[Optional[int]] = set()
    
    for scored in scored_slots:
        slot = scored['slot']

        # Get available doctors for this slot (Fix C: boost mode never filters)
        doctors = data_store.get_doctors_for_slot(
            slot['weekday'],
            slot['shift_code']
        )

        # In preferred_doctor boost mode: never skip slots; use fallback if no doctor
        if not doctors and preferred_doctor:
            doctors = [preferred_doctor]  # Use requested name as fallback
        if not doctors:
            doctors = ['دکتر عمومی']  # Generic fallback so we never empty results

        # Select best matching doctor for this slot
        doctor = None
        preferred_doctor = request_params.get('preferred_doctor')
        preferred_doctor_id = request_params.get('preferred_doctor_id')
        
        if preferred_doctor and doctors:
            # 1. Prefer reference match (doctor_id)
            if preferred_doctor_id is not None:
                for shift_doc in doctors:
                    resolved = data_store.resolve_shift_doctor_to_reference(shift_doc)
                    if resolved and str(resolved[0]) == str(preferred_doctor_id):
                        doctor = resolved[1]  # Use display name from reference
                        logger.debug(f"Using preferred doctor '{doctor}' (ref_id: {preferred_doctor_id}) for slot "
                                   f"{slot['weekday']} {slot['shift_code']}")
                        break
            # 2. Fallback: fuzzy match
            if not doctor:
                from app.utils.text import find_best_doctor_match
                match_result = find_best_doctor_match(preferred_doctor, doctors, min_confidence=0.6)
                if match_result:
                    matched_doctor, confidence, match_type = match_result
                    doctor = matched_doctor
                    logger.debug(f"Using preferred doctor '{doctor}' for slot "
                               f"{slot['weekday']} {slot['shift_code']} "
                               f"(match: {match_type}, confidence: {confidence:.2f})")
        
        # Otherwise pick first available doctor
        if not doctor and doctors:
            doctor = doctors[0]

        # Resolve doctor_id and doctor_name from reference
        from app.engine.doctor_matcher import match_doctor
        shift_doctor_name = doctor
        ref = match_doctor(shift_doctor_name, getattr(data_store, "doctor_ref_by_norm", {}))
        if ref:
            slot_doctor_id = ref.doctor_id
            slot_doctor_name = ref.doctor_name_display
        else:
            slot_doctor_id = None
            slot_doctor_name = f"دکتر {shift_doctor_name}" if shift_doctor_name else "دکتر عمومی"
        
        # Create unique key to avoid duplicate recommendations
        slot_key = (slot['weekday'], slot['shift_code'], slot['start_time'])
        if slot_key in seen_combinations:
            continue
        seen_combinations.add(slot_key)
        
        # Create recommendation
        breakdown = ScoreBreakdown(
            urgency_score=scored['urgency_score'],
            financial_score=scored['financial_score'],
            availability_score=scored['availability_score'],
            complexity_fit_score=scored['complexity_fit_score'],
            time_score=scored['time_score'],
            total_score=scored['total_score']
        )
        
        recommendation = SlotRecommendation(
            weekday=slot['weekday'],
            shift_code=slot['shift_code'],
            start_time=slot['start_time'],
            end_time=slot['end_time'],
            doctor=slot_doctor_name,
            doctor_id=slot_doctor_id,
            score=scored['total_score'],
            breakdown=breakdown,
            service_duration_min=service_duration,
            service_complexity=scored['service_complexity'],
            reason_strings_fa=_build_reason_strings_fa(scored)
        )
        all_doctor_ids.add(slot_doctor_id)

        # Attach explainable scoring trace (non-breaking)
        if hasattr(recommendation, "__dict__"):
            recommendation.__dict__["_score_components"] = scored.get("components", {})
            recommendation.__dict__["_preferred_doctor_boost"] = scored.get("preferred_doctor_boost", 0.0)
            recommendation.__dict__["_total_base"] = scored.get("total_base", scored.get("total_score", 0.0))
            recommendation.__dict__["preferred_doctor_match"] = scored.get("preferred_doctor_match", False)
        
        # Optional diversify: limit how many slots per doctor_id we keep,
        # but only when there is actual doctor diversity.
        can_diversify = len([d for d in all_doctor_ids if d is not None]) > 1
        did = slot_doctor_id
        if can_diversify and did is not None and doctor_counts[did] >= max_per_doctor:
            continue
        if did is not None:
            doctor_counts[did] += 1

        recommendations.append(recommendation)
        
        # Stop when we have enough
        if len(recommendations) >= top_n:
            break
    
    # Snapshot 3: FINAL recommendations diversity snapshot
    if recommendations:
        total_candidates = len(recommendations)
        unique_weekdays = len({r.weekday for r in recommendations})
        unique_shifts = len({r.shift_code for r in recommendations})
        unique_doctors = len({r.doctor_id for r in recommendations if getattr(r, "doctor_id", None) is not None})
        sample = [
            (r.weekday, r.start_time, r.shift_code, getattr(r, "doctor_id", None), r.doctor)
            for r in recommendations[:30]
        ]
        logger.info(
            "FINAL_RECOMMENDATIONS summary: total=%d, unique_weekdays=%d, unique_shifts=%d, unique_doctors=%d; sample=%r",
            total_candidates, unique_weekdays, unique_shifts, unique_doctors, sample
        )
    
    logger.info(f"Generated {len(recommendations)} recommendations")

    # Fix A: Fallback when recommendations empty but we have candidate slots
    if not recommendations and scored_slots:
        from app.engine.doctor_matcher import match_doctor
        fallback_slots = scored_slots[:top_n]
        for scored in fallback_slots:
            slot = scored['slot']
            doctors = data_store.get_doctors_for_slot(slot['weekday'], slot['shift_code'])
            doctor = (doctors[0] if doctors else 'دکتر عمومی')
            ref = match_doctor(doctor, getattr(data_store, "doctor_ref_by_norm", {}))
            if ref:
                slot_doctor_id = ref.doctor_id
                slot_doctor_name = ref.doctor_name_display
            else:
                slot_doctor_id = None
                slot_doctor_name = f"دکتر {doctor}" if doctor and doctor != "دکتر عمومی" else "دکتر عمومی"
            breakdown = ScoreBreakdown(
                urgency_score=scored['urgency_score'],
                financial_score=scored['financial_score'],
                availability_score=scored['availability_score'],
                complexity_fit_score=scored['complexity_fit_score'],
                total_score=scored['total_score']
            )
            rec = SlotRecommendation(
                weekday=slot['weekday'],
                shift_code=slot['shift_code'],
                start_time=slot['start_time'],
                end_time=slot['end_time'],
                doctor=slot_doctor_name,
                doctor_id=slot_doctor_id,
                score=scored['total_score'],
                breakdown=breakdown,
                service_duration_min=service_duration,
                service_complexity=scored.get('service_complexity', 0.5),
                reason_strings_fa=_build_reason_strings_fa(scored)
            )
            if hasattr(rec, "__dict__"):
                rec.__dict__["_reason_codes"] = ["fallback_no_scored_slots"]
                rec.__dict__["_score_components"] = scored.get("components", {})
                rec.__dict__["_preferred_doctor_boost"] = scored.get("preferred_doctor_boost", 0.0)
                rec.__dict__["_total_base"] = scored.get("total_base", scored.get("total_score", 0.0))
            recommendations.append(rec)
        logger.info(f"Applied fallback: {len(recommendations)} slots with reason_codes=['fallback_no_scored_slots']")

    # Create result
    from app.utils.text_normalize import normalize_doctor_name, normalize_doctor_key

    # Attach doctor_norm key to each recommendation (surname-based)
    for rec in recommendations:
        if hasattr(rec, "__dict__"):
            rec.__dict__["doctor_norm"] = normalize_doctor_key(getattr(rec, "doctor", "") or "")

    # Recompute preferred_doctor_match / preferred_doctor_boost AFTER doctor_id is assigned
    pref_id = getattr(original_request, "preferred_doctor_id", None)
    pref_name = getattr(original_request, "preferred_doctor", None)

    for rec in recommendations:
        match = False
        did = getattr(rec, "doctor_id", None)
        doc_name = getattr(rec, "doctor", None)

        # 1) Prefer id-based match when available
        try:
            if pref_id is not None and did is not None and int(did) == int(pref_id):
                match = True
        except (TypeError, ValueError):
            match = False

        # 2) Fallback to name-based match when no id or id-mismatch
        if not match and pref_name and doc_name:
            try:
                norm_pref = normalize_doctor_name(pref_name)
                norm_doc = normalize_doctor_name(doc_name)
                match = bool(norm_pref and norm_doc and norm_pref == norm_doc)
            except Exception:
                match = False

        boost = 0.05 if match else 0.0

        if hasattr(rec, "__dict__"):
            # Update metadata on recommendation object
            rec.__dict__["preferred_doctor_match"] = match
            rec.__dict__["preferred_doctor_boost"] = boost

            base = rec.__dict__.get("_total_base", None)
            try:
                if base is not None:
                    base_f = float(base)
                    total = max(0.0, min(1.0, base_f + boost))
                    rec.__dict__["_preferred_doctor_boost"] = boost
                    rec.__dict__["_total_base"] = base_f
                    comps = rec.__dict__.setdefault("_score_components", {})
                    comps["preferred_doctor_boost"] = boost
                    # Keep components["total"] in sync if present
                    comps["total"] = total
                    rec.score = total
                else:
                    # If we don't have base, just bump the score field
                    rec.score = min(1.0, float(rec.score) + boost)
            except Exception:
                # If anything goes wrong, at least keep the match flag
                pass

    # Re-sort recommendations by updated score (descending)
    recommendations.sort(key=lambda r: float(getattr(r, "score", 0.0)), reverse=True)

    result = SchedulingResult(
        top_recommendations=recommendations,
        inputs_echo=original_request,
        total_slots_evaluated=len(all_slots)
    )
    
    return result


def recommendations_to_csv(recommendations: List[SlotRecommendation], output_path: str):
    """
    Save recommendations to CSV file.
    
    Args:
        recommendations: List of slot recommendations
        output_path: Path to output CSV file
    """
    import csv
    
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow([
            'weekday', 'shift_code', 'start_time', 'end_time', 'doctor_id', 'doctor', 'doctor_norm',
            'total_score', 'urgency_score', 'financial_score',
            'availability_score', 'complexity_fit_score', 'time_score',
            'preferred_doctor_match', 'preferred_doctor_boost',
            'service_duration_min', 'service_complexity'
        ])
        
        # Write rows
        for rec in recommendations:
            writer.writerow([
                rec.weekday,
                rec.shift_code,
                rec.start_time,
                rec.end_time,
                getattr(rec, "doctor_id", ""),
                rec.doctor,
                getattr(rec, "doctor_norm", ""),
                f"{rec.score:.3f}",
                f"{rec.breakdown.urgency_score:.3f}",
                f"{rec.breakdown.financial_score:.3f}",
                f"{rec.breakdown.availability_score:.3f}",
                f"{rec.breakdown.complexity_fit_score:.3f}",
                f"{rec.breakdown.time_score:.3f}",
                getattr(rec, "preferred_doctor_match", False),
                getattr(rec, "_preferred_doctor_boost", 0.0),
                rec.service_duration_min,
                f"{rec.service_complexity:.3f}"
            ])
    
    logger.info(f"Saved {len(recommendations)} recommendations to {output_path}")


def _recommend_slots_v2(
    request: Union[SchedulingRequest, CaseContext],
    data_store: DataStore,
    top_n: int = 10,
    slot_minutes: int = 30
) -> SchedulingResult:
    """
    Generate slot recommendations using v2 value-based scheduling.
    
    V2 combines Patient Total Value Score (TVS) with Slot Fit Score.
    Provides full decision trace for explainability.
    
    Args:
        request: SchedulingRequest or CaseContext with patient info
        data_store: Loaded data store
        top_n: Number of top recommendations to return
        slot_minutes: Slot duration in minutes
        
    Returns:
        SchedulingResult with top recommendations (v1-compatible format)
    """
    from app.engine.tvs.allocator import recommend_slots_v2
    from app.config import weights_config
    
    # Extract request parameters from CaseContext if needed
    if isinstance(request, CaseContext):
        from app.integrations.crm.adapter import extract_request_params
        request_params = extract_request_params(request)
        service_name = request.request.service_name
        preferred_weekday = request.request.desired_weekday or request.patient.preferred_weekday
        original_request = request.request
    else:
        # Legacy SchedulingRequest
        request_params = {
            'service_name': request.service_name,
            'service_id': getattr(request, 'service_id', None),
            'insurance_name': getattr(request, 'insurance_name', None),
            'backlog_title': getattr(request, 'backlog_title', None),
            'preferred_doctor': request.preferred_doctor,
            'preferred_weekday': getattr(request, 'preferred_weekday', None)
        }
        service_name = request.service_name
        preferred_weekday = request_params.get('preferred_weekday')
        original_request = request
    
    service_lookup_key = request_params.get("service_id") or service_name
    logger.info(f"[V2] Generating recommendations for service: {service_name} (lookup: {service_lookup_key})")
    
    # Generate all possible slots
    all_slots = generate_all_slots(slot_minutes)
    logger.info(f"[V2] Generated {len(all_slots)} total slots")
    
    # Filter by preferred weekday if specified
    if preferred_weekday:
        from app.utils.fa_normalize import normalize_fa
        preferred_norm = normalize_fa(preferred_weekday)
        all_slots = [
            slot for slot in all_slots
            if normalize_fa(slot['weekday']) == preferred_norm
        ]
        logger.info(f"[V2] Filtered to {len(all_slots)} slots for preferred weekday")
    
    # Get v2 weights from config
    v2_weights = weights_config.get_v2_weights()
    
    # Call v2 allocator
    v2_result = recommend_slots_v2(
        slots=all_slots,
        request_params=request_params,
        data_store=data_store,
        top_k=top_n,
        weights_config=v2_weights
    )
    
    recommendations_v2 = v2_result['recommendations']
    meta = v2_result['meta']
    
    logger.info(f"[V2] Generated {len(recommendations_v2)} recommendations "
                f"(patient_tvs={meta.get('patient_tvs', 0):.3f})")
    
    # Convert v2 recommendations to v1-compatible format
    recommendations = []
    
    for rec_v2 in recommendations_v2:
        slot = rec_v2.slot
        trace = rec_v2.trace
        
        # Get available doctors for this slot
        doctors = data_store.get_doctors_for_slot(
            slot['weekday'],
            slot['shift_code']
        )
        
        if not doctors:
            continue
        
        # Select doctor (prefer preferred_doctor if specified)
        doctor = None
        preferred_doctor = request_params.get('preferred_doctor')
        
        if preferred_doctor and doctors:
            from app.utils.text import find_best_doctor_match
            match_result = find_best_doctor_match(preferred_doctor, doctors, min_confidence=0.6)
            if match_result:
                matched_doctor, confidence, match_type = match_result
                doctor = matched_doctor
        
        if not doctor and doctors:
            doctor = doctors[0]

        # Resolve doctor_id and doctor_name from reference
        from app.engine.doctor_matcher import match_doctor
        shift_doctor_name = doctor
        ref = match_doctor(shift_doctor_name, getattr(data_store, "doctor_ref_by_norm", {}))
        if ref:
            slot_doctor_id = ref.doctor_id
            slot_doctor_name = ref.doctor_name_display
        else:
            slot_doctor_id = None
            slot_doctor_name = f"دکتر {shift_doctor_name}" if shift_doctor_name else "دکتر عمومی"
        
        # Get service info (accepts service_id or service_name)
        service_info = data_store.get_service_info(service_lookup_key) or {}
        service_duration = service_info.get('default_duration_min', 30)
        service_complexity = service_info.get('complexity_weight', 0.5)
        
        # Create v1-compatible breakdown (using v2 slot fit scores for backward compatibility)
        breakdown = ScoreBreakdown(
            urgency_score=trace.slot_urgency,
            financial_score=trace.slot_financial,
            availability_score=trace.slot_availability,
            complexity_fit_score=trace.slot_complexity_fit,
            total_score=rec_v2.final_score  # V2: final_score becomes v1's total_score
        )
        
        # Build reason strings from v2 trace
        reasons_v2 = [
            f"فوریت درمان: {trace.slot_urgency:.0%}",
            f"اولویت بیمه: {trace.slot_financial:.0%}",
            f"امتیاز دسترسی پزشک: {trace.slot_availability:.0%}",
            f"تطابق پیچیدگی شیفت: {trace.slot_complexity_fit:.0%}",
        ]
        recommendation = SlotRecommendation(
            weekday=slot['weekday'],
            shift_code=slot['shift_code'],
            start_time=slot['start_time'],
            end_time=slot['end_time'],
            doctor=slot_doctor_name,
            doctor_id=slot_doctor_id,
            score=rec_v2.final_score,
            breakdown=breakdown,
            service_duration_min=service_duration,
            service_complexity=service_complexity,
            reason_strings_fa=reasons_v2
        )
        
        # Optionally attach v2 trace (as extra metadata if schema supports)
        # This preserves v2 explainability while maintaining v1 compatibility
        if hasattr(recommendation, '__dict__'):
            recommendation.__dict__['_v2_trace'] = {
                'patient_tvs': rec_v2.patient_tvs,
                'slot_fit_score': rec_v2.slot_fit_score,
                'cis': trace.cis,
                'ltvs': trace.ltvs,
                'risk': trace.risk,
                'fair': trace.fair,
                'urg': trace.urg,
                'engine_version': 'v2'
            }
        
        recommendations.append(recommendation)
    
    logger.info(f"[V2] Converted {len(recommendations)} recommendations to v1 format")

    # Fix A (v2): Fallback when recommendations empty but we have slots
    if not recommendations and all_slots:
        from app.engine.doctor_matcher import match_doctor
        service_info = data_store.get_service_info(service_lookup_key) or {}
        service_duration = service_info.get('default_duration_min', 30)
        for slot in all_slots[:top_n]:
            doctors = data_store.get_doctors_for_slot(slot['weekday'], slot['shift_code'])
            doctor = (doctors[0] if doctors else 'دکتر عمومی')
            ref = match_doctor(doctor, getattr(data_store, "doctor_ref_by_norm", {}))
            if ref:
                slot_doctor_id = ref.doctor_id
                slot_doctor_name = ref.doctor_name_display
            else:
                slot_doctor_id = None
                slot_doctor_name = f"دکتر {doctor}" if doctor and doctor != "دکتر عمومی" else "دکتر عمومی"
            breakdown = ScoreBreakdown(
                urgency_score=0.5,
                financial_score=0.5,
                availability_score=0.5,
                complexity_fit_score=0.5,
                total_score=0.0
            )
            rec = SlotRecommendation(
                weekday=slot['weekday'],
                shift_code=slot['shift_code'],
                start_time=slot['start_time'],
                end_time=slot['end_time'],
                doctor=slot_doctor_name,
                doctor_id=slot_doctor_id,
                score=0.0,
                breakdown=breakdown,
                service_duration_min=service_duration,
                service_complexity=0.5
            )
            if hasattr(rec, '__dict__'):
                rec.__dict__['_reason_codes'] = ['fallback_no_scored_slots']
            recommendations.append(rec)
        logger.info(f"[V2] Applied fallback: {len(recommendations)} slots")

    # Create result (v1-compatible)
    result = SchedulingResult(
        top_recommendations=recommendations,
        inputs_echo=original_request,
        total_slots_evaluated=meta.get('total_evaluated', len(all_slots))
    )
    
    # Attach v2 metadata if result supports it
    if hasattr(result, '__dict__'):
        result.__dict__['_v2_meta'] = meta
    
    return result

