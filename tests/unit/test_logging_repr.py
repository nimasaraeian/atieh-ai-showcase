"""
Tests for logging with %r (repr) - no manual quote concatenation.
Ensures logs do not contain typos or malformed normalized values.
"""
import logging
import pytest

from app.engine.recommender import recommend_slots
from app.engine.scoring import DataStore
from app.schemas.scheduling import SchedulingRequest
from app.utils.doctor_name import normalize_doctor_name
from app.utils.log_sanitize import safe_norm_doctor


def test_normalize_doctor_name_strips_trailing_quote():
    assert normalize_doctor_name("دکتر احمدی'") == "احمدی"


def test_safe_norm_doctor_trailing_quote_produces_clean_output():
    """When preferred_doctor has trailing quote, normalized logged value is exact, no extra quote."""
    preferred = "دکتر " + "احمدی" + "'"
    norm = safe_norm_doctor(preferred)
    expected = "احمدی"
    assert norm == expected, f"Expected {expected!r}, got {norm!r}"


def test_preferred_doctor_logging_does_not_double_quote(caplog):
    caplog.set_level(logging.INFO)

    preferred = "دکتر احمدی'"
    norm = safe_norm_doctor(preferred)

    logger = logging.getLogger("test_logger")
    logger.info("Preferred doctor=%r normalized=%r", preferred, norm)

    text = "\n".join(r.message for r in caplog.records)
    # Must not produce double-quote artifact
    bad = "احمدی" + "''"
    assert bad not in text


def test_preferred_doctor_flow_logs_do_not_contain_typos(caplog):
    """Logs from preferred-doctor flow must not contain recoommendations, recommmendations, noot found."""
    ds = DataStore()
    ds.load_from_csv("data/outputs")
    req = SchedulingRequest(
        service_name="کشیدن دندان",
        preferred_doctor="دکتر احمدی",
        preferred_weekday="شنبه",
    )
    with caplog.at_level(logging.WARNING):
        recommend_slots(request=req, data_store=ds, top_n=5)

    typo1 = "recoommendations"
    typo2 = "recommmendations"
    typo3 = "noot found"
    log_text = caplog.text.lower()
    assert typo1 not in log_text, f"Log contains typo: {typo1}"
    assert typo2 not in log_text, f"Log contains typo: {typo2}"
    assert typo3 not in log_text, f"Log contains typo: {typo3}"
