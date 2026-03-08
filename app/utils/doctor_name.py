"""Definitive doctor name normalizer - safe, no dangerous replaces."""
import re
import unicodedata

_PREFIXES = (
    "دکتر", "دكتر", "دکتر.", "دكتر.", "د.", "Dr.", "DR.", "dr.",
)

_QUOTE_CHARS = {
    "'", "\u2019", "\u2018", "`", "\u00b4", "\uff07", "\u02bc", "\u02b9",
    '"', "\u201c", "\u201d", "\u201e", "\u301d", "\u301e",
}

_ZW_CHARS = {"\u200c", "\u200d"}  # ZWNJ / ZWJ

# Correct common typos in doctor names (نامووجود->ناموجود, غیررموجود->غیرموجود)
_KNOWN_TYPOS = {"نامووجود": "ناموجود", "غیررموجود": "غیرموجود"}


def normalize_doctor_name(text: str) -> str:
    if text is None:
        return ""

    s = str(text).strip()

    # Unicode normalize (prevents weird composed forms)
    s = unicodedata.normalize("NFKC", s)

    # unify Arabic/Persian letters
    s = s.replace("ي", "ی").replace("ك", "ک")

    # remove zero-width chars
    for ch in _ZW_CHARS:
        s = s.replace(ch, "")

    # remove quotes anywhere (this fixes احمدی' and similar)
    s = "".join(c for c in s if c not in _QUOTE_CHARS)

    # remove common prefixes
    s_strip = s.strip()
    for p in _PREFIXES:
        if s_strip.startswith(p):
            s_strip = s_strip[len(p):].strip()
            break
    s = s_strip

    # collapse spaces
    s = re.sub(r"\s+", " ", s).strip()

    # Correct common typos
    s = _KNOWN_TYPOS.get(s, s)

    return s
