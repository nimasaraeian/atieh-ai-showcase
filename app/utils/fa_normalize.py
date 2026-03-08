"""Persian text normalization utilities."""
import re


def normalize_fa(text):
    """
    Normalize Persian/Farsi text for consistent matching.
    
    - Remove Kashida (ـ) - decorative elongation character
    - Remove zero-width and directional marks
    - Convert Arabic characters to Persian equivalents
    - Convert Persian/Arabic digits to ASCII (0-9)
    - Remove Arabic diacritics (vowel marks)
    - Trim and collapse whitespace
    
    Args:
        text: Input text string
        
    Returns:
        Normalized text string
    """
    if text is None:
        return ""
    
    text = str(text)
    
    # Remove Kashida (Arabic tatweel) - decorative elongation
    text = text.replace('\u0640', '')  # ـ
    text = text.replace('ـ', '')  # Just in case
    
    # Remove zero-width characters
    text = text.replace('\u200c', '')  # Zero-width non-joiner (ZWNJ)
    text = text.replace('\u200d', '')  # Zero-width joiner (ZWJ)
    text = text.replace('\u200b', '')  # Zero-width space
    text = text.replace('\u200e', '')  # Left-to-right mark
    text = text.replace('\u200f', '')  # Right-to-left mark
    text = text.replace('\ufeff', '')  # Zero-width no-break space (BOM)
    text = text.replace('\u202a', '')  # Left-to-right embedding
    text = text.replace('\u202b', '')  # Right-to-left embedding
    text = text.replace('\u202c', '')  # Pop directional formatting
    text = text.replace('\u202d', '')  # Left-to-right override
    text = text.replace('\u202e', '')  # Right-to-left override
    
    # Remove Arabic diacritics (vowel marks)
    diacritics = [
        '\u064b',  # Fathatan
        '\u064c',  # Dammatan
        '\u064d',  # Kasratan
        '\u064e',  # Fatha
        '\u064f',  # Damma
        '\u0650',  # Kasra
        '\u0651',  # Shadda
        '\u0652',  # Sukun
    ]
    for diacritic in diacritics:
        text = text.replace(diacritic, '')
    
    # Convert Arabic characters to Persian
    text = text.replace('ي', 'ی')  # Arabic yeh to Persian yeh
    text = text.replace('ى', 'ی')  # Alef maksura to Persian yeh
    text = text.replace('ك', 'ک')  # Arabic kaf to Persian kaf
    text = text.replace('ؤ', 'و')  # Waw with hamza
    text = text.replace('ئ', 'ی')  # Yeh with hamza
    text = text.replace('إ', 'ا')  # Alef with hamza below
    text = text.replace('أ', 'ا')  # Alef with hamza above
    text = text.replace('آ', 'ا')  # Alef with madda
    
    # Convert Persian digits to ASCII
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    ascii_digits = '0123456789'
    for pd, ad in zip(persian_digits, ascii_digits):
        text = text.replace(pd, ad)
    
    # Convert Arabic-Indic digits to ASCII
    arabic_digits = '٠١٢٣٤٥٦٧٨٩'
    for ard, ad in zip(arabic_digits, ascii_digits):
        text = text.replace(ard, ad)
    
    # Trim and collapse whitespace
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    
    return text


_QUOTE_CHARS = {
    "'", "\u2019", "\u2018", "`", "\u00b4", "\uff07", "\u02bc", "\u02b9",
    '"', "\u201c", "\u201d", "\u201e", "\u301d", "\u301e",
}


def normalize_fa_text(text: str) -> str:
    """
    Canonical Persian text normalization: safe for doctor names and general text.
    - Returns "" for None/empty
    - Removes zero-width chars, tatweel
    - Normalizes ي->ی, ك->ک
    - Collapses spaces
    - Removes quotes and stray apostrophes (e.g. trailing "'")
    """
    if text is None or not str(text).strip():
        return ""
    s = normalize_fa(str(text))
    # Remove quotes and apostrophes
    s = "".join(c for c in s if c not in _QUOTE_CHARS)
    return re.sub(r'\s+', ' ', s).strip()


def extract_tags(text):
    """
    Extract tags in parentheses from Persian text.
    
    Args:
        text: Input text like "دکتر احمدی (اطفال)"
        
    Returns:
        Tuple of (cleaned_text, tags_list)
        Example: ("دکتر احمدی", ["اطفال"])
    """
    tags = []
    # Find all content in parentheses
    pattern = r'\([^)]+\)'
    matches = re.findall(pattern, text)
    
    for match in matches:
        # Remove parentheses and normalize
        tag = normalize_fa(match.strip('()'))
        if tag:
            tags.append(tag)
    
    # Remove all parentheses content from original text
    cleaned = re.sub(pattern, '', text)
    cleaned = normalize_fa(cleaned)
    
    return cleaned, tags


def split_doctors(text):
    """
    Split a text field containing multiple doctor names.
    
    Splits on:
    - Hyphen/dash: '-', '–', '—'
    - Newlines
    - Multiple consecutive spaces (3+)
    
    Args:
        text: Text containing multiple doctor names
        
    Returns:
        List of normalized doctor names
    """
    if not text:
        return []
    
    text = str(text)
    
    # Replace various dashes with standard separator
    text = text.replace('–', '|')
    text = text.replace('—', '|')
    text = text.replace('-', '|')
    
    # Replace newlines with separator
    text = text.replace('\n', '|')
    text = text.replace('\r', '|')
    
    # Replace multiple spaces with separator
    text = re.sub(r'\s{3,}', '|', text)
    
    # Split and normalize
    doctors = [normalize_fa(d) for d in text.split('|')]
    
    # Filter out empty strings
    doctors = [d for d in doctors if d]
    
    return doctors
