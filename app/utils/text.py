"""
Enhanced text normalization utilities for robust matching.
Provides comprehensive Persian/Farsi text normalization with doctor name support.
"""
import re
from typing import Optional

_DOCTOR_PREFIX_RE = re.compile(r"^\s*(دکتر|دكتر|دکتر\.|dr\.|dr)\s+", flags=re.IGNORECASE)


def normalize_fa_text(text: Optional[str]) -> str:
    """
    Comprehensive Persian/Farsi text normalization.
    
    Handles:
    - Case normalization (lowercase)
    - Arabic to Persian character conversion (ي→ی, ك→ک)
    - Zero-width and invisible characters (ZWNJ, ZWJ, BOM, etc.)
    - Tatweel (kashida) removal
    - Whitespace normalization
    - Diacritic removal
    
    Args:
        text: Input text string
        
    Returns:
        Normalized text string (empty string if None)
        
    Examples:
        >>> normalize_fa_text("دکتر  احمدی")
        'دکتر احمدی'
        >>> normalize_fa_text("محمدي")  # Arabic yeh
        'محمدی'
    """
    if text is None:
        return ""
    
    text = str(text)
    
    # Step 1: Convert to lowercase
    text = text.lower()
    
    # Step 2: Strip leading/trailing whitespace
    text = text.strip()
    
    # Step 3: Replace Arabic characters with Persian equivalents
    # Arabic yeh (ي) and yeh with hamza (ئ) -> Persian yeh (ی)
    text = text.replace('ي', 'ی')  # Arabic yeh
    text = text.replace('ى', 'ی')  # Alef maksura
    text = text.replace('ئ', 'ی')  # Yeh with hamza above
    
    # Arabic kaf (ك) -> Persian kaf (ک)
    text = text.replace('ك', 'ک')  # Arabic kaf
    
    # Other Arabic to Persian conversions
    text = text.replace('ؤ', 'و')  # Waw with hamza
    text = text.replace('إ', 'ا')  # Alef with hamza below
    text = text.replace('أ', 'ا')  # Alef with hamza above
    text = text.replace('آ', 'ا')  # Alef with madda
    text = text.replace('ة', 'ه')  # Teh marbuta to heh
    
    # Step 4: Remove zero-width and invisible characters
    invisible_chars = [
        '\u200c',  # Zero-width non-joiner (ZWNJ) - common in Persian
        '\u200d',  # Zero-width joiner (ZWJ)
        '\u200b',  # Zero-width space
        '\u200e',  # Left-to-right mark
        '\u200f',  # Right-to-left mark
        '\ufeff',  # Zero-width no-break space (BOM)
        '\u202a',  # Left-to-right embedding
        '\u202b',  # Right-to-left embedding
        '\u202c',  # Pop directional formatting
        '\u202d',  # Left-to-right override
        '\u202e',  # Right-to-left override
        '\u2060',  # Word joiner
        '\u2061',  # Function application
        '\u2062',  # Invisible times
        '\u2063',  # Invisible separator
        '\u2064',  # Invisible plus
    ]
    
    for char in invisible_chars:
        text = text.replace(char, '')
    
    # Step 5: Remove tatweel (kashida) - decorative elongation
    text = text.replace('\u0640', '')  # ـ (Arabic tatweel)
    text = text.replace('ـ', '')       # Explicit character
    
    # Step 6: Remove Arabic diacritics (vowel marks)
    diacritics = [
        '\u064b',  # Fathatan (ً)
        '\u064c',  # Dammatan (ٌ)
        '\u064d',  # Kasratan (ٍ)
        '\u064e',  # Fatha (َ)
        '\u064f',  # Damma (ُ)
        '\u0650',  # Kasra (ِ)
        '\u0651',  # Shadda (ّ)
        '\u0652',  # Sukun (ْ)
        '\u0653',  # Maddah (ٓ)
        '\u0654',  # Hamza above (ٔ)
        '\u0655',  # Hamza below (ٕ)
    ]
    
    for diacritic in diacritics:
        text = text.replace(diacritic, '')
    
    # Step 7: Collapse multiple whitespace to single space
    text = re.sub(r'\s+', ' ', text)
    
    # Step 8: Final trim
    text = text.strip()
    
    return text


def name_contains(a: str, b: str) -> bool:
    """
    True if normalized a contains normalized b OR vice versa.
    Useful for 'شعله نعمتی' vs 'نعمتی'
    """
    from app.utils.doctor_name import normalize_doctor_name as _norm
    na = _norm(a or "")
    nb = _norm(b or "")
    if not na or not nb:
        return False
    return (nb in na) or (na in nb)


def normalize_doctor_name(name: Optional[str]) -> str:
    """Re-export from app.utils.doctor_name for backward compatibility."""
    from app.utils.doctor_name import normalize_doctor_name as _impl
    return _impl(name)


def compare_doctor_names(name1: Optional[str], name2: Optional[str]) -> tuple[bool, float, str]:
    """
    Compare two doctor names with multiple matching strategies.
    
    Strategies (in order):
    1. Exact match: Normalized names are identical
    2. Contains match: One name contains the other
    3. Word match: All words from shorter name appear in longer name
    
    Args:
        name1: First doctor name
        name2: Second doctor name
        
    Returns:
        Tuple of (is_match, confidence, match_type)
        
    Examples:
        >>> compare_doctor_names("دکتر احمدی", "احمدی")
        (True, 1.0, 'exact')
        >>> normalize_doctor_name("د. محمدی")
        'محمدی'
        >>> normalize_doctor_name("Dr. Smith")
        'smith'
        >>> normalize_doctor_name("دكتر نعمتي")  # Arabic variants
        'نعمتی'
        >>> normalize_doctor_name("دکتر  احمدی  ")  # Extra spaces
        'احمدی'
    """
    if not name1 or not name2:
        return (False, 0.0, 'no_match')
    
    norm1 = normalize_doctor_name(name1)
    norm2 = normalize_doctor_name(name2)
    
    if not norm1 or not norm2:
        return (False, 0.0, 'no_match')
    
    if norm1 == norm2:
        return (True, 1.0, 'exact')
    
    if norm1 in norm2:
        return (True, len(norm1) / len(norm2), 'contains')
    if norm2 in norm1:
        return (True, len(norm2) / len(norm1), 'contains')
    
    words1 = set(norm1.split())
    words2 = set(norm2.split())
    if words1 and words2:
        shorter = words1 if len(words1) <= len(words2) else words2
        longer = words2 if len(words1) <= len(words2) else words1
        if shorter.issubset(longer):
            return (True, len(shorter) / len(longer), 'word_match')
    
    return (False, 0.0, 'no_match')


def find_best_doctor_match(
    query: str,
    candidates: list,
    min_confidence: float = 0.6
) -> Optional[tuple]:
    """
    Find the best matching doctor name from a list of candidates.
    
    Args:
        query: Doctor name to search for
        candidates: List of candidate doctor names
        min_confidence: Minimum confidence threshold (0.0-1.0)
        
    Returns:
        Tuple of (matched_name, confidence, match_type) or None if no match
        
    Examples:
        >>> find_best_doctor_match("احمدی", ["دکتر احمدی", "محمدی"])
        ('دکتر احمدی', 1.0, 'exact')
    """
    if not query or not candidates:
        return None
    
    best_match = None
    best_confidence = 0.0
    best_type = 'no_match'
    
    for candidate in candidates:
        is_match, confidence, match_type = compare_doctor_names(query, candidate)
        
        if is_match and confidence > best_confidence:
            best_match = candidate
            best_confidence = confidence
            best_type = match_type
            
            # If exact match, return immediately
            if match_type == 'exact' and confidence == 1.0:
                return (best_match, best_confidence, best_type)
    
    # Return best match if confidence meets threshold
    if best_match and best_confidence >= min_confidence:
        return (best_match, best_confidence, best_type)
    
    return None
