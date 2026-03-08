"""Utilities for normalizing person names, especially doctor names."""
import re
from app.utils.fa_normalize import normalize_fa


def normalize_doctor_name(name: str) -> str:
    """
    Normalize doctor name for consistent matching.
    
    Removes prefixes like:
    - دکتر (Persian)
    - دكتر (Arabic variant)
    - د. (abbreviated)
    - Dr. or Dr (English)
    
    Then applies standard Persian normalization.
    
    Args:
        name: Doctor name (possibly with prefix)
        
    Returns:
        Normalized name without prefix
        
    Examples:
        'دکتر احمدی' -> 'احمدی'
        'د. نعمتی' -> 'نعمتی'
        'احمدی' -> 'احمدی'
    """
    if not name:
        return ""
    
    # First apply basic Persian normalization
    name = normalize_fa(str(name))
    
    # Remove common doctor prefixes (case-insensitive)
    # Order matters: check longer patterns first
    prefixes = [
        'دکتر',   # Persian doctor
        'دكتر',   # Arabic kaf variant
        'د.',     # Abbreviated
        'dr.',    # English abbreviated
        'dr',     # English
    ]
    
    name_lower = name.lower()
    
    for prefix in prefixes:
        if name_lower.startswith(prefix):
            # Remove prefix and any following whitespace
            name = name[len(prefix):].strip()
            name_lower = name.lower()
    
    # Trim and collapse multiple spaces
    name = re.sub(r'\s+', ' ', name.strip())
    
    return name


def get_doctor_name_variants(name: str) -> list:
    """
    Get common variants of a doctor name for fuzzy matching.
    
    Args:
        name: Doctor name
        
    Returns:
        List of name variants to try matching
        
    Examples:
        'احمدی' -> ['احمدی', 'دکتر احمدی', 'د. احمدی']
    """
    if not name:
        return []
    
    # Normalize the input
    normalized = normalize_doctor_name(name)
    
    # Generate variants
    variants = [
        normalized,                    # Base normalized form
        f"دکتر {normalized}",          # With Persian prefix
        f"د. {normalized}",            # With abbreviated prefix
        normalized.lower(),            # Lowercase
    ]
    
    # Remove duplicates while preserving order
    seen = set()
    unique_variants = []
    for v in variants:
        v_lower = v.lower()
        if v_lower not in seen:
            seen.add(v_lower)
            unique_variants.append(v)
    
    return unique_variants


def match_doctor_name(
    query: str,
    candidates: list,
    threshold: float = 0.6
) -> tuple:
    """
    Find the best matching doctor name from a list of candidates.
    
    Uses normalized matching with prefix removal.
    
    Args:
        query: Doctor name to search for
        candidates: List of candidate doctor names
        threshold: Minimum similarity threshold (0.0-1.0)
        
    Returns:
        Tuple of (matched_name, confidence_score, match_type)
        Returns (None, 0.0, 'no_match') if no good match found
        
    Match types:
    - 'exact': Exact match after normalization
    - 'contains': One name contains the other
    - 'partial': Partial word match
    - 'no_match': No good match found
    """
    if not query or not candidates:
        return (None, 0.0, 'no_match')
    
    query_norm = normalize_doctor_name(query).lower()
    
    # Try exact match first
    for candidate in candidates:
        candidate_norm = normalize_doctor_name(candidate).lower()
        if query_norm == candidate_norm:
            return (candidate, 1.0, 'exact')
    
    # Try contains match
    best_match = None
    best_score = 0.0
    best_type = 'no_match'
    
    for candidate in candidates:
        candidate_norm = normalize_doctor_name(candidate).lower()
        
        # Check if query contains candidate or vice versa
        if query_norm in candidate_norm:
            score = len(query_norm) / len(candidate_norm)
            if score > best_score:
                best_match = candidate
                best_score = score
                best_type = 'contains'
        elif candidate_norm in query_norm:
            score = len(candidate_norm) / len(query_norm)
            if score > best_score:
                best_match = candidate
                best_score = score
                best_type = 'contains'
    
    if best_match and best_score >= threshold:
        return (best_match, best_score, best_type)
    
    return (None, 0.0, 'no_match')
