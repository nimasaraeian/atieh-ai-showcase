import math

from app.engine.scoring import DataStore, score_slot


def test_score_components_sum_to_total():
    ds = DataStore()
    ds.load_from_csv()  # uses Config paths

    # pick a known slot shape (same as generate_all_slots produces)
    slot = {"weekday": "شنبه", "shift_code": "D", "start_time": "08:00", "end_time": "08:30"}

    # service info minimal
    service_info = {"complexity_weight": 0.5}

    # request params minimal (no preferred boost)
    request_params = {"insurance_name": None, "backlog_title": None, "preferred_doctor_id": None}

    scored = score_slot(slot, service_info, request_params, ds)
    comps = scored.get("components", {})

    assert "total_base" in comps
    assert "total" in comps

    # base = sum(weighted components (including time))
    base_sum = (
        comps["urgency"]
        + comps["financial"]
        + comps["availability"]
        + comps["complexity_fit"]
        + comps["time"]
    )
    assert math.isclose(base_sum, comps["total_base"], rel_tol=1e-9, abs_tol=1e-9)

    # total = total_base + boost (boost is 0 here)
    assert math.isclose(comps["total_base"] + comps.get("preferred_doctor_boost", 0.0), comps["total"], rel_tol=1e-9, abs_tol=1e-9)

    # scored total_score should match comps total
    assert math.isclose(scored["total_score"], comps["total"], rel_tol=1e-9, abs_tol=1e-9)
