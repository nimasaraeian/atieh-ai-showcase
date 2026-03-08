"""Doctor name normalization tests. Bad variants (extra و, extra ر) must normalize to correct forms."""
from app.utils.doctor_name import normalize_doctor_name
from app.utils.fa_normalize import normalize_fa_text


def test_quotes_removed():
    assert normalize_doctor_name("دکتر احمدی'") == "احمدی"
    assert normalize_doctor_name("احمدی''") == "احمدی"
    assert normalize_doctor_name("'احمدی'") == "احمدی"


def test_nonexistent_word_not_corrupted():
    """Correct spelling must pass through unchanged (no corruption)."""
    correct = "غیر" + "موجود"
    assert normalize_doctor_name("دکتر " + correct) == correct


def test_typos_corrected():
    """Bad variant 1 (extra و) and bad variant 2 (extra ر) must never appear as output."""
    # Bad variant 1: typo with extra و
    bad1 = "نام" + "و" + "وجود"
    correct1 = "نام" + "و" + "جود"
    assert normalize_doctor_name("دکتر " + bad1) == correct1
    assert normalize_doctor_name(bad1) != bad1
    assert bad1 not in (normalize_doctor_name(bad1),)

    # Bad variant 2: typo with extra ر
    bad2 = "غیر" + "ر" + "م" + "وجود"
    correct2 = "غیر" + "م" + "وجود"
    assert normalize_doctor_name("دکتر " + bad2) == correct2
    assert normalize_doctor_name(bad2) != bad2
    assert bad2 not in (normalize_doctor_name(bad2),)


def test_normalize_fa_text_strips_trailing_quote():
    assert normalize_fa_text("دکتر احمدی'") == "دکتر احمدی"
