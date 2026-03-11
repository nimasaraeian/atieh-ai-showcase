# -*- coding: utf-8 -*-
"""
Service normalization for Atieh AI analytics.

Maps noisy free-text service/treatment values to clean categories for
dashboard analytics, filters, and reporting.

Categories: معاینه، ترمیم، اندو، جرمگیری، کشیدن، جراحی، ایمپلنت، روکش، لمینت،
            قالبگیری، پست، بلیچینگ، ارتودنسی، پروتز، پریو، اطفال، کنترل، سایر
"""
import re
from dataclasses import dataclass
from typing import Optional, Tuple

# ─── Standard service categories (Persian) ─────────────────────────────────
SERVICE_CATEGORIES = [
    "معاینه",
    "ترمیم",
    "اندو",
    "جرمگیری",
    "کشیدن",
    "جراحی",
    "ایمپلنت",
    "روکش",
    "لمینت",
    "قالبگیری",
    "پست",
    "بلیچینگ",
    "ارتودنسی",
    "پروتز",
    "پریو",
    "اطفال",
    "کنترل",
    "سایر",
]

DEFAULT_CATEGORY = "سایر"


# ─── Keyword → category mapping (order matters: first match wins) ───────────
# Format: (keyword_pattern, category, subtype_hint)
# Use lowercase Persian for matching; we normalize input
CATEGORY_KEYWORDS = [
    # معاینه
    (r"معاینه", "معاینه", None),
    (r"معاينه", "معاینه", None),
    (r"consultation", "معاینه", None),
    # ترمیم
    (r"ترمیم", "ترمیم", None),
    (r"ترميم", "ترمیم", None),
    (r"ترمبم", "ترمیم", None),
    (r"پرکردن", "ترمیم", None),
    (r"کامپوزیت", "ترمیم", None),
    (r"filling", "ترمیم", None),
    (r"restoration", "ترمیم", None),
    # اندو
    (r"اندو", "اندو", None),
    (r"ریشه", "اندو", None),
    (r"عصب", "اندو", None),
    (r"ری اندو", "اندو", "ری اندو"),
    (r"root", "اندو", None),
    (r"endo", "اندو", None),
    # جرمگیری
    (r"جرم", "جرمگیری", None),
    (r"بروساژ", "جرمگیری", None),
    (r"scaling", "جرمگیری", None),
    (r"پولیش", "جرمگیری", None),
    # کشیدن
    (r"کشیدن", "کشیدن", None),
    (r"کشيدن", "کشیدن", None),
    (r"extraction", "کشیدن", None),
    # جراحی
    (r"جراحی", "جراحی", None),
    (r"جراحي", "جراحی", None),
    (r"surgery", "جراحی", None),
    (r"جراح", "جراحی", None),
    # ایمپلنت
    (r"ایمپلنت", "ایمپلنت", None),
    (r"ايمپلنت", "ایمپلنت", None),
    (r"implant", "ایمپلنت", None),
    (r"کاشت", "ایمپلنت", None),
    (r"imp\b", "ایمپلنت", None),
    (r"im\b", "ایمپلنت", None),
    # روکش
    (r"روکش", "روکش", None),
    (r"رو کش", "روکش", None),
    (r"crown", "روکش", None),
    (r"کره", "روکش", "واحد کره"),
    # لمینت
    (r"لمینت", "لمینت", None),
    (r"ونیر", "لمینت", None),
    (r"veneer", "لمینت", None),
    # قالبگیری
    (r"قالبگیری", "قالبگیری", None),
    (r"قالب", "قالبگیری", None),
    (r"قالب گيري", "قالبگیری", None),
    # پست
    (r"پست", "پست", None),
    (r"post", "پست", None),
    (r"فایبر", "پست", "فایبر پست"),
    # بلیچینگ
    (r"بلیچینگ", "بلیچینگ", None),
    (r"bleaching", "بلیچینگ", None),
    # ارتودنسی
    (r"ارتودنسی", "ارتودنسی", None),
    (r"ارتودنسي", "ارتودنسی", None),
    # پروتز
    (r"پروتز", "پروتز", None),
    (r"prosthesis", "پروتز", None),
    (r"بریج", "پروتز", None),
    # پریو
    (r"پریو", "پریو", None),
    (r"پريو", "پریو", None),
    (r"periodont", "پریو", None),
    # اطفال
    (r"اطفال", "اطفال", None),
    (r"کودک", "اطفال", None),
    (r"pediatric", "اطفال", None),
    # کنترل
    (r"کنترل", "کنترل", None),
    (r"فیشور", "کنترل", None),
    (r"فيشور", "کنترل", None),
    (r"cl\b", "کنترل", "فیشور"),
]


# ─── Noise patterns (exclude or mark as noise) ─────────────────────────────
NOISE_PATTERNS = [
    r"^09\d{9}$",  # Iranian mobile
    r"^9\d{9}$",
    r"^\d{10,11}$",  # Phone-like
    r"^\d{4}-\d{2}-\d{2}",  # Date prefix
    r"^\d{2}:\d{2}",  # Time
    r"^\d+$",  # Pure number
    r"^\.\s*",  # Starts with dot
    r"^;\s*",  # Starts with semicolon
    r"^\|+$",  # Pipe only
    r"^میا[dد]$",  # میاد (coming)
    r"^کنسلی",  # Cancellation
    r"^تماس گرفته شود",  # Call note
    r"^کنترل بعد",  # Control-after (often noise)
    r"^وقت تلفنی$",
    r"^وقت نیم ساعته$",
    r"^بیان$",  # "say" / note
]

CANCELLATION_KEYWORDS = ["کنسلی", "کنسل", "cancelled", "cancel"]

# Duration patterns to strip before classification
DURATION_PATTERNS = [
    r"\d+\s*دقیقه\s*",
    r"\d+\s*دفیقه\s*",
    r"\d+\s*س\s*(?:اعته)?\s*",
    r"\d+\.?\d*\s*س\s*",
    r"\d+/\d+\s*س\s*",
    r"\d+\s*ساعت\s*",
    r"\d+\s*ساعته\s*",
    r"\d+/\d+\s*ساعته\s*",
    r"\d+\.\d+\s*س\s*",
    r"\d+:\d+\s*",  # time like 9:30
    r"\d+/\d+\s*",  # fraction like 1/5
]


def _normalize_persian(s: str) -> str:
    """Normalize Persian text for matching."""
    if not s:
        return ""
    s = s.strip()
    # Arabic to Persian
    s = s.replace("ي", "ی").replace("ك", "ک").replace("ة", "ه")
    s = s.replace("ى", "ی").replace("ؤ", "و").replace("إ", "ا").replace("أ", "ا")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _is_phone(s: str) -> bool:
    """Check if string looks like a phone number."""
    digits = re.sub(r"\D", "", s)
    return len(digits) >= 10 and len(digits) <= 11


def _is_date(s: str) -> bool:
    """Check if string looks like a date."""
    return bool(re.search(r"\d{4}-\d{2}-\d{2}", s)) or bool(re.search(r"\d{4}/\d{2}/\d{2}", s))


def _is_mostly_digits(s: str) -> bool:
    """Check if string is mostly digits."""
    if not s:
        return True
    digits = sum(1 for c in s if c.isdigit())
    return digits >= len(s) * 0.7


def _is_cancellation_note(s: str) -> bool:
    """Check if text is primarily a cancellation note."""
    n = _normalize_persian(s).lower()
    for kw in CANCELLATION_KEYWORDS:
        if kw in n and len(n) < 50:
            return True
    return False


def _strip_durations(text: str) -> str:
    """Remove duration-like substrings to improve category matching."""
    t = text
    for pat in DURATION_PATTERNS:
        t = re.sub(pat, " ", t, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", t).strip()


def _extract_duration_minutes(text: str) -> Optional[int]:
    """Extract approximate duration in minutes if present."""
    # 45 دقیقه
    m = re.search(r"(\d+)\s*دقیقه", text)
    if m:
        return int(m.group(1))
    # 1 س, 1.5 س
    m = re.search(r"(\d+\.?\d*)\s*س\b", text)
    if m:
        return int(float(m.group(1)) * 60)
    return None


@dataclass
class ServiceNormalizeResult:
    """Result of service normalization."""
    clean_service_category: str
    clean_service_subtype: Optional[str]
    duration_hint_minutes: Optional[int]
    is_noise: bool
    is_cancellation_note: bool


def normalize_service(raw: Optional[str]) -> ServiceNormalizeResult:
    """
    Normalize a raw service/treatment string into a clean category.

    Returns:
        ServiceNormalizeResult with clean_service_category, subtype,
        duration_hint, is_noise, is_cancellation_note.
    """
    if not raw or not str(raw).strip():
        return ServiceNormalizeResult(
            clean_service_category=DEFAULT_CATEGORY,
            clean_service_subtype=None,
            duration_hint_minutes=None,
            is_noise=True,
            is_cancellation_note=False,
        )

    s = str(raw).strip()
    if len(s) < 2:
        return ServiceNormalizeResult(
            clean_service_category=DEFAULT_CATEGORY,
            clean_service_subtype=None,
            duration_hint_minutes=None,
            is_noise=True,
            is_cancellation_note=False,
        )

    # Noise checks
    if _is_phone(s):
        return ServiceNormalizeResult(
            clean_service_category=DEFAULT_CATEGORY,
            clean_service_subtype=None,
            duration_hint_minutes=None,
            is_noise=True,
            is_cancellation_note=False,
        )
    if _is_date(s) and len(s) < 25:
        return ServiceNormalizeResult(
            clean_service_category=DEFAULT_CATEGORY,
            clean_service_subtype=None,
            duration_hint_minutes=None,
            is_noise=True,
            is_cancellation_note=False,
        )
    if _is_mostly_digits(s):
        return ServiceNormalizeResult(
            clean_service_category=DEFAULT_CATEGORY,
            clean_service_subtype=None,
            duration_hint_minutes=None,
            is_noise=True,
            is_cancellation_note=False,
        )

    is_cancellation = _is_cancellation_note(s)
    duration_hint = _extract_duration_minutes(s)
    stripped = _strip_durations(s)
    normalized = _normalize_persian(stripped).lower()

    if not stripped:
        return ServiceNormalizeResult(
            clean_service_category=DEFAULT_CATEGORY,
            clean_service_subtype=None,
            duration_hint_minutes=duration_hint,
            is_noise=True,
            is_cancellation_note=is_cancellation,
        )

    # Match keywords (first match wins)
    for pattern, category, subtype in CATEGORY_KEYWORDS:
        if re.search(pattern, normalized):
            return ServiceNormalizeResult(
                clean_service_category=category,
                clean_service_subtype=subtype,
                duration_hint_minutes=duration_hint,
                is_noise=False,
                is_cancellation_note=is_cancellation,
            )

    # No keyword match - check if it looks like pure admin/duration
    if len(normalized) < 5 and re.match(r"^[\d\.\/\:\s]+$", normalized):
        return ServiceNormalizeResult(
            clean_service_category=DEFAULT_CATEGORY,
            clean_service_subtype=None,
            duration_hint_minutes=duration_hint,
            is_noise=True,
            is_cancellation_note=is_cancellation,
        )

    # Unclassified: map to سایر
    return ServiceNormalizeResult(
        clean_service_category=DEFAULT_CATEGORY,
        clean_service_subtype=None,
        duration_hint_minutes=duration_hint,
        is_noise=False,
        is_cancellation_note=is_cancellation,
    )


def get_clean_service_category(raw: Optional[str]) -> str:
    """Convenience: return only the clean category string."""
    return normalize_service(raw).clean_service_category
