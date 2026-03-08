"""
Production-Grade Slot Recommender
==================================
Generates slot recommendations with doctor assignments, confidence scoring,
and diversity ranking using mock CRM data.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class SlotWithDoctor:
    """Represents a time slot with assigned doctor and metadata."""
    
    def __init__(
        self,
        start_datetime: datetime,
        duration_minutes: int,
        doctor_id: str,
        doctor_name: str,
        schedule_id: str,
        shift_code: str
    ):
        self.start_datetime = start_datetime
        self.duration_minutes = duration_minutes
        self.doctor_id = doctor_id
        self.doctor_name = doctor_name
        self.schedule_id = schedule_id
        self.shift_code = shift_code
        self.end_datetime = start_datetime + timedelta(minutes=duration_minutes)
        self.confidence = 0.0
        self.reason_codes = []
    
    def __repr__(self):
        return f"<Slot {self.start_datetime} | {self.doctor_name} | conf={self.confidence:.2f}>"


class ProductionSlotRecommender:
    """
    Production-grade slot recommender with doctor assignment and confidence scoring.
    Uses mock CRM data (doctors, schedules, blocks, appointments).
    """
    
    def __init__(self, mock_data_dir: Optional[Path] = None):
        """Initialize recommender with mock data directory."""
        if mock_data_dir is None:
            # Auto-detect
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent
            mock_data_dir = project_root / "data" / "mock"
        
        self.mock_data_dir = Path(mock_data_dir)
        logger.info(f"ProductionSlotRecommender initialized with data_dir: {self.mock_data_dir}")
        
        # Load mock data
        self.doctors = self._load_json("doctors.json")
        self.schedules = self._load_json("schedules.json")
        self.blocks = self._load_json("blocks.json")
        
        logger.info(f"Loaded: {len(self.doctors)} doctors, {len(self.schedules)} schedules, {len(self.blocks)} blocks")
    
    def _load_json(self, filename: str) -> List[Dict]:
        """Load JSON file with UTF-8 encoding."""
        filepath = self.mock_data_dir / filename
        if not filepath.exists():
            logger.warning(f"File not found: {filepath}")
            return []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            return []
    
    def get_available_slots_with_doctors(
        self,
        start_date: datetime,
        end_date: datetime,
        duration_minutes: int,
        existing_appointments: List[Dict],
        max_candidates: int = 60
    ) -> List[SlotWithDoctor]:
        """
        Generate available slots with doctor assignments.
        
        Args:
            start_date: Start date for search
            end_date: End date for search
            duration_minutes: Appointment duration
            existing_appointments: List of existing appointments (to avoid overlap)
            max_candidates: Maximum candidate slots to generate
            
        Returns:
            List of SlotWithDoctor objects
        """
        logger.debug(f"Generating slots from {start_date.date()} to {end_date.date()}")
        
        slots = []
        
        # Filter schedules within date range
        relevant_schedules = [
            sch for sch in self.schedules
            if start_date.date() <= datetime.strptime(sch['date'], '%Y-%m-%d').date() <= end_date.date()
            and sch.get('is_available', True)
        ]
        
        logger.debug(f"Found {len(relevant_schedules)} relevant schedules")
        
        # Generate slots from each schedule
        for schedule in relevant_schedules:
            if len(slots) >= max_candidates:
                break
            
            try:
                # Parse schedule date and time
                sch_date = datetime.strptime(schedule['date'], '%Y-%m-%d')
                start_time_parts = schedule['start_time'].split(':')
                end_time_parts = schedule['end_time'].split(':')
                
                start_hour = int(start_time_parts[0])
                start_min = int(start_time_parts[1]) if len(start_time_parts) > 1 else 0
                end_hour = int(end_time_parts[0])
                
                # Create datetime objects
                current_slot = sch_date.replace(
                    hour=start_hour,
                    minute=start_min,
                    second=0,
                    microsecond=0,
                    tzinfo=timezone.utc
                )
                
                shift_end = sch_date.replace(
                    hour=end_hour,
                    minute=0,
                    second=0,
                    microsecond=0,
                    tzinfo=timezone.utc
                )
                
                # Generate 30-minute slots within this shift
                while current_slot < shift_end:
                    slot_end = current_slot + timedelta(minutes=duration_minutes)
                    
                    # Skip lunch hours (13:00-14:00)
                    if 13 <= current_slot.hour < 14:
                        current_slot += timedelta(minutes=30)
                        continue
                    
                    # Skip if slot doesn't fit before shift end
                    if slot_end > shift_end:
                        break
                    
                    # Check for overlaps with existing appointments
                    has_conflict = False
                    for appt in existing_appointments:
                        appt_start = datetime.fromisoformat(appt['appointment_date'])
                        if appt_start.tzinfo is None:
                            appt_start = appt_start.replace(tzinfo=timezone.utc)
                        appt_end = appt_start + timedelta(minutes=appt.get('duration_minutes', 30))
                        
                        # Check overlap
                        if not (slot_end <= appt_start or current_slot >= appt_end):
                            has_conflict = True
                            break
                    
                    # Check for overlaps with blocks
                    if not has_conflict:
                        for block in self.blocks:
                            if block['doctor_id'] != schedule['doctor_id']:
                                continue
                            
                            block_start = datetime.fromisoformat(block['start_datetime'])
                            block_end = datetime.fromisoformat(block['end_datetime'])
                            
                            if block_start.tzinfo is None:
                                block_start = block_start.replace(tzinfo=timezone.utc)
                            if block_end.tzinfo is None:
                                block_end = block_end.replace(tzinfo=timezone.utc)
                            
                            # Check overlap
                            if not (slot_end <= block_start or current_slot >= block_end):
                                has_conflict = True
                                break
                    
                    # If no conflict, create slot
                    if not has_conflict:
                        slot = SlotWithDoctor(
                            start_datetime=current_slot,
                            duration_minutes=duration_minutes,
                            doctor_id=schedule['doctor_id'],
                            doctor_name=schedule['doctor_name'],
                            schedule_id=schedule['id'],
                            shift_code=schedule['shift_code']
                        )
                        slots.append(slot)
                        
                        if len(slots) >= max_candidates:
                            break
                    
                    # Move to next slot
                    current_slot += timedelta(minutes=30)
                
            except Exception as e:
                logger.warning(f"Error processing schedule {schedule.get('id')}: {e}")
                continue
        
        logger.info(f"Generated {len(slots)} candidate slots with doctor assignments")
        return slots
    
    def calculate_slot_confidence(
        self,
        slot: SlotWithDoctor,
        patient_priority: float,
        urgency_level: str,
        existing_appointments: List[Dict],
        days_ahead: int
    ) -> float:
        """
        Calculate confidence score for a slot (0.0-1.0).
        
        Scoring factors:
        - base = 0.55
        - +0.15 if slot within next 3 days (available soon)
        - +0.10 if morning slot (08:00-12:00) and urgency high
        - +0.10 if slot aligns with patient priority (high priority → earlier)
        - -0.15 if doctor has many appointments that day (load factor)
        - -0.10 if slot adjacent to block boundary (risk)
        """
        confidence = 0.55  # Base confidence
        reason_codes = []
        
        now = datetime.now(timezone.utc)
        days_until = (slot.start_datetime - now).days
        hour = slot.start_datetime.hour
        
        # +0.15 if available soon (within 3 days)
        if days_until <= 3:
            confidence += 0.15
            reason_codes.append("AVAILABLE_SOON")
        
        # +0.10 if morning slot and high urgency
        if 8 <= hour < 12:
            reason_codes.append("MORNING_SLOT")
            if urgency_level in ['high', 'critical']:
                confidence += 0.10
                reason_codes.append("URGENT_MORNING")
        elif 14 <= hour < 17:
            reason_codes.append("AFTERNOON_SLOT")
        else:
            reason_codes.append("EVENING_SLOT")
        
        # +0.10 if slot timing aligns with priority
        if patient_priority >= 85:
            # High priority patients should get earlier slots
            if days_until <= 7:
                confidence += 0.10
                reason_codes.append("HIGH_PRIORITY_MATCH")
        
        # -0.15 if doctor has many appointments that day (load factor)
        slot_date = slot.start_datetime.date()
        doctor_appts_today = sum(
            1 for appt in existing_appointments
            if (
                appt.get('doctor_id') == slot.doctor_id or
                appt.get('patient_id')  # Fallback if no doctor_id
            ) and datetime.fromisoformat(appt['appointment_date']).date() == slot_date
        )
        
        if doctor_appts_today >= 5:
            confidence -= 0.15
            reason_codes.append("HIGH_DOCTOR_LOAD")
        elif doctor_appts_today <= 2:
            confidence += 0.05
            reason_codes.append("LOW_DOCTOR_LOAD")
        
        # -0.10 if slot adjacent to block boundary
        for block in self.blocks:
            if block['doctor_id'] != slot.doctor_id:
                continue
            
            block_start = datetime.fromisoformat(block['start_datetime'])
            block_end = datetime.fromisoformat(block['end_datetime'])
            
            if block_start.tzinfo is None:
                block_start = block_start.replace(tzinfo=timezone.utc)
            if block_end.tzinfo is None:
                block_end = block_end.replace(tzinfo=timezone.utc)
            
            # Check if slot is within 30 minutes of block
            time_to_block_start = (block_start - slot.end_datetime).total_seconds() / 60
            time_from_block_end = (slot.start_datetime - block_end).total_seconds() / 60
            
            if 0 < time_to_block_start <= 30 or 0 < time_from_block_end <= 30:
                confidence -= 0.10
                reason_codes.append("NEAR_BLOCK")
                break
        
        # Check doctor rating boost
        doctor = next((d for d in self.doctors if d['id'] == slot.doctor_id), None)
        if doctor and doctor.get('rating', 0) >= 4.8:
            confidence += 0.05
            reason_codes.append("TOP_RATED_DOCTOR")
        
        # Clamp to [0.0, 1.0]
        confidence = max(0.0, min(1.0, confidence))
        
        slot.confidence = confidence
        slot.reason_codes = reason_codes
        
        return confidence
    
    def rank_and_diversify_slots(
        self,
        slots: List[SlotWithDoctor],
        max_slots: int,
        days_ahead: int
    ) -> List[SlotWithDoctor]:
        """
        Rank slots by confidence and apply diversity rules.
        
        Diversity rules:
        - Avoid more than 2 consecutive back-to-back slots
        - Avoid all slots from same doctor if multiple available
        - Spread across different days when days_ahead > 7
        """
        if not slots:
            return []
        
        # Sort by confidence (descending)
        slots.sort(key=lambda s: s.confidence, reverse=True)
        
        selected = []
        doctors_used = set()
        days_used = set()
        last_slot_time = None
        consecutive_count = 0
        
        for slot in slots:
            if len(selected) >= max_slots:
                break
            
            slot_date = slot.start_datetime.date()
            
            # Diversity rule 1: Limit consecutive slots
            if last_slot_time:
                time_diff = (slot.start_datetime - last_slot_time).total_seconds() / 60
                if time_diff <= 30:  # Consecutive
                    consecutive_count += 1
                    if consecutive_count >= 2:
                        # Skip this slot to avoid 3+ consecutive
                        continue
                else:
                    consecutive_count = 0
            
            # Diversity rule 2: Limit slots per doctor (max 2)
            doctor_count = sum(1 for s in selected if s.doctor_id == slot.doctor_id)
            if doctor_count >= 2 and len(doctors_used) > 1:
                # Skip if this doctor already has 2 slots and we have other doctors
                continue
            
            # Diversity rule 3: Spread across days (for longer ranges)
            if days_ahead > 7:
                # Try to have at least 1 slot per week
                week_num = (slot_date - slots[0].start_datetime.date()).days // 7
                week_count = sum(
                    1 for s in selected
                    if (s.start_datetime.date() - slots[0].start_datetime.date()).days // 7 == week_num
                )
                if week_count >= 2 and len(selected) < max_slots - 2:
                    # Already have 2 slots this week, prefer other weeks
                    continue
            
            # Add slot
            selected.append(slot)
            doctors_used.add(slot.doctor_id)
            days_used.add(slot_date)
            last_slot_time = slot.start_datetime
        
        logger.info(f"Selected {len(selected)} diversified slots from {len(doctors_used)} doctors")
        return selected
    
    def get_doctor_daily_load(
        self,
        doctor_id: str,
        date: datetime,
        existing_appointments: List[Dict]
    ) -> int:
        """Count appointments for a doctor on a specific day."""
        target_date = date.date()
        count = sum(
            1 for appt in existing_appointments
            if datetime.fromisoformat(appt['appointment_date']).date() == target_date
        )
        return count


def recommend_slots_with_doctors(
    start_date: datetime,
    end_date: datetime,
    duration_minutes: int,
    existing_appointments: List[Dict[str, Any]],
    patient_priority: float,
    urgency_level: str,
    days_ahead: int,
    max_slots: int = 5
) -> List[SlotWithDoctor]:
    """
    Main function to get slot recommendations with doctor assignments.
    
    Args:
        start_date: Start of search range
        end_date: End of search range
        duration_minutes: Appointment duration
        existing_appointments: Current appointments to avoid
        patient_priority: Patient priority score (0-100)
        urgency_level: Urgency level (low, medium, high, critical)
        days_ahead: Days ahead parameter
        max_slots: Maximum slots to return
        
    Returns:
        List of ranked SlotWithDoctor objects
    """
    recommender = ProductionSlotRecommender()
    
    # Step 1: Generate candidate slots
    logger.debug("Step 1: Generating candidate slots...")
    candidates = recommender.get_available_slots_with_doctors(
        start_date=start_date,
        end_date=end_date,
        duration_minutes=duration_minutes,
        existing_appointments=existing_appointments,
        max_candidates=60
    )
    
    if not candidates:
        logger.warning("No candidate slots found")
        return []
    
    logger.debug(f"Generated {len(candidates)} candidate slots")
    
    # Step 2: Calculate confidence for each slot
    logger.debug("Step 2: Calculating confidence scores...")
    for slot in candidates:
        recommender.calculate_slot_confidence(
            slot=slot,
            patient_priority=patient_priority,
            urgency_level=urgency_level,
            existing_appointments=existing_appointments,
            days_ahead=days_ahead
        )
    
    # Step 3: Rank and diversify
    logger.debug("Step 3: Ranking and diversifying...")
    final_slots = recommender.rank_and_diversify_slots(
        slots=candidates,
        max_slots=max_slots,
        days_ahead=days_ahead
    )
    
    logger.info(f"Final recommendation: {len(final_slots)} slots")
    return final_slots
