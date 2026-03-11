def compute_ai_slot_score(slot, patient_profile):
    financial_score = patient_profile.get("financial_value_score", 0.5)

    payment_type = str(
        patient_profile.get("payment_type")
        or patient_profile.get("insurance")
        or "INSURANCE"
    ).upper()

    if payment_type == "CASH":
        payment_score = 1.0
    else:
        payment_score = 0.7

    days_until_slot = slot.get("days_until_slot", 7)

    if days_until_slot == 0:
        time_score = 1.0
    elif days_until_slot <= 2:
        time_score = 0.9
    elif days_until_slot <= 5:
        time_score = 0.8
    else:
        time_score = 0.6

    score = (
        financial_score * 0.5
        + payment_score * 0.3
        + time_score * 0.2
    )

    return round(score, 3)
