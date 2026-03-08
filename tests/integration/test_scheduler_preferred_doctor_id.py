from app.engine.scoring import DataStore
from app.engine.recommender import recommend_slots
from app.schemas.scheduling import SchedulingRequest
from app.engine.scheduler import build_schedule_draft


def test_scheduler_respects_preferred_doctor_id():
    ds = DataStore()
    ds.load_from_csv()

    req = SchedulingRequest(
        service_name="ترمیم",
        preferred_doctor="دکتر نعمتی",
        desired_weekday="شنبه",
    )

    result = recommend_slots(req, ds, top_n=10, slot_minutes=30, engine_version="v1")
    assert result.top_recommendations

    # Ensure doctor_id exists in recommendations
    assert any(getattr(r, "doctor_id", None) is not None for r in result.top_recommendations)

    draft = build_schedule_draft(result.top_recommendations, req, ds)
    assert draft is not None
    assert "نعمتی" in (draft.doctor or "")
