def compute_ai_slot_score(slot, patient_profile):

    financial = patient_profile.get("financial_value_score", 0.5)
    payment = slot.get("payment_score", 0.5)
    doctor = slot.get("doctor_match_score", 0.5)
    time = slot.get("time_score", 0.5)

    score = (
        financial * 0.35
        + payment * 0.25
        + doctor * 0.20
        + time * 0.20
    )

    return score
