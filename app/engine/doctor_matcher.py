from app.loaders.doctors_reference_csv import norm_fa, DoctorRef

def match_doctor(raw_name: str, ref_map: dict[str, DoctorRef]) -> DoctorRef | None:
    q = norm_fa(raw_name)
    if not q:
        return None

    if q in ref_map:
        return ref_map[q]

    for k, d in ref_map.items():
        if k.endswith(" " + q) or k.startswith(q + " ") or (" " + q + " ") in (" " + k + " "):
            return d

    return None
