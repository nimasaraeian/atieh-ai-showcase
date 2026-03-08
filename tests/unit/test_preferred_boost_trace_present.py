from app.engine.scoring import DataStore
from app.engine.recommender import recommend_slots
from app.schemas.scheduling import SchedulingRequest


def test_preferred_boost_is_exposed_in_trace():
    ds = DataStore()
    ds.load_from_csv()

    req = SchedulingRequest(
        service_name="کشیدن دندان",
        preferred_doctor="دکتر شعله نعمتی",
    )

    result = recommend_slots(req, ds, top_n=10, slot_minutes=30, engine_version="v1")
    assert result.top_recommendations, "No recommendations returned"

    # At least one slot in top-k should have boost metadata
    boosted = []
    for rec in result.top_recommendations:
        boost = getattr(rec, "_preferred_doctor_boost", None)
        if boost is None and hasattr(rec, "__dict__"):
            boost = rec.__dict__.get("_preferred_doctor_boost")
        if boost and boost > 0:
            boosted.append(rec)

    assert boosted, "Expected at least one boosted recommendation in top-k"
