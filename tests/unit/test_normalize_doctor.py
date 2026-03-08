from app.utils.text_normalize import normalize_doctor_name


def test_trailing_quote_simple():
    assert normalize_doctor_name("دکتر احمدی'") == "احمدی"


def test_trailing_quote_with_spaces_and_arabic_prefix():
    assert normalize_doctor_name(" دكتر   احمدی'' ") == "احمدی"


def test_full_name_preserved_without_prefix():
    assert normalize_doctor_name("دکتر شعله نعمتی") == "شعله نعمتی"

