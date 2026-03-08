from app.utils.text import normalize_doctor_name


def test_normalize_removes_quotes():
    assert normalize_doctor_name("احمدی'") == "احمدی"
    assert normalize_doctor_name("دکتر احمدی") == "احمدی"
    assert normalize_doctor_name("دكتر احمدي") == "احمدی"
