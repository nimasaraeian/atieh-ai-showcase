"""
Row hashing utilities for deduplication.
"""
import hashlib
from typing import Any, Optional


def row_hash(*parts: Any) -> str:
    """
    Generate SHA256 hash from row parts for deduplication.
    
    Args:
        *parts: Variable number of values to include in hash
    
    Returns:
        Hex string of SHA256 hash
    
    Example:
        hash_val = row_hash(name, phone, date, doctor, service)
    """
    # Normalize all parts to strings
    normalized_parts = []
    
    for part in parts:
        if part is None:
            normalized_parts.append("")
        elif isinstance(part, str):
            # Strip and lowercase for case-insensitive comparison
            normalized_parts.append(part.strip().lower())
        else:
            # Convert to string
            normalized_parts.append(str(part))
    
    # Join with pipe separator
    combined = "|".join(normalized_parts)
    
    # Generate SHA256 hash
    hash_obj = hashlib.sha256(combined.encode('utf-8'))
    
    return hash_obj.hexdigest()


def safe_row_hash(*parts: Any) -> Optional[str]:
    """
    Safe version that returns None if insufficient data for hash.
    Requires at least 3 non-empty parts.
    """
    non_empty = [p for p in parts if p is not None and str(p).strip()]
    
    if len(non_empty) < 3:
        # Not enough data for reliable deduplication
        return None
    
    return row_hash(*parts)
