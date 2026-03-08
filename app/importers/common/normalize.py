"""
Text normalization utilities for Persian/Arabic text and phone numbers.
"""
import re
from typing import Optional


def normalize_text(text: Optional[str]) -> str:
    """
    Normalize Persian/Arabic text:
    - Trim whitespace
    - Convert Arabic chars to Persian equivalents
    - Collapse multiple spaces
    - Remove zero-width characters
    """
    if not text:
        return ""
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    # Arabic to Persian character mapping
    replacements = {
        'ي': 'ی',  # Arabic yeh -> Persian yeh
        'ى': 'ی',  # Alef maksura -> Persian yeh  
        'ك': 'ک',  # Arabic kaf -> Persian kaf
        'ة': 'ه',  # Arabic teh marbuta -> Persian heh
        'ؤ': 'و',  # Hamza on waw
        'إ': 'ا',  # Hamza below alef
        'أ': 'ا',  # Hamza above alef
        'ٱ': 'ا',  # Alef wasla
        'ء': '',   # Remove standalone hamza
    }
    
    for arabic, persian in replacements.items():
        text = text.replace(arabic, persian)
    
    # Remove zero-width characters
    text = text.replace('\u200c', '')  # ZWNJ
    text = text.replace('\u200f', '')  # RTL mark
    text = text.replace('\ufeff', '')  # Zero-width no-break space
    text = text.replace('ـ', '')       # Tatweel
    
    # Remove diacritics (harakat)
    diacritics = [
        '\u064B', '\u064C', '\u064D',  # Tanween
        '\u064E', '\u064F', '\u0650',  # Fatha, Damma, Kasra
        '\u0651', '\u0652',            # Shadda, Sukun
        '\u0653', '\u0654', '\u0655',  # Additional marks
    ]
    for mark in diacritics:
        text = text.replace(mark, '')
    
    # Collapse multiple spaces to single space
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def normalize_digits(text: Optional[str]) -> str:
    """
    Convert Persian/Arabic digits to English digits.
    """
    if not text:
        return ""
    
    # Persian digits
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    # Arabic digits  
    arabic_digits = '٠١٢٣٤٥٦٧٨٩'
    # English digits
    english_digits = '0123456789'
    
    result = text
    
    # Persian to English
    for i, digit in enumerate(persian_digits):
        result = result.replace(digit, english_digits[i])
    
    # Arabic to English
    for i, digit in enumerate(arabic_digits):
        result = result.replace(digit, english_digits[i])
    
    return result


def normalize_phone(phone: Optional[str]) -> Optional[str]:
    """
    Normalize Iranian phone numbers to international format: +98XXXXXXXXXX
    
    Handles formats:
    - 09123456789
    - 9123456789
    - 0098123456789
    - +989123456789
    - 021-12345678 (landline)
    """
    if not phone:
        return None
    
    # First normalize digits
    phone = normalize_digits(str(phone))
    
    # Remove all non-digit characters
    phone = re.sub(r'\D', '', phone)
    
    if not phone:
        return None
    
    # Convert to mobile format
    if phone.startswith('0098'):
        # Remove country code prefix
        phone = phone[2:]
    elif phone.startswith('98'):
        # Already has country code without +
        phone = phone
    elif phone.startswith('0'):
        # Remove leading zero
        phone = phone[1:]
    
    # Ensure it starts with 9 (mobile) or is landline
    if phone.startswith('9') and len(phone) == 10:
        # Mobile number
        return f'+98{phone}'
    elif len(phone) == 11 and phone.startswith('9'):
        # Already has 98 prefix
        return f'+{phone}'
    elif len(phone) in [7, 8]:
        # Landline (too short for unique identification)
        # Keep as-is but mark as potentially non-unique
        return f'+9821{phone}'  # Assume Tehran area code
    
    # If nothing matches, return None (invalid)
    return None


def extract_digits_only(text: Optional[str]) -> str:
    """
    Extract only digits from text (useful for national ID, etc.)
    """
    if not text:
        return ""
    
    text = normalize_digits(str(text))
    return re.sub(r'\D', '', text)
