"""
Patient creation helpers with schema validation.

Ensures only valid fields are passed to Patient() constructor.
"""

# Strict whitelist of valid Patient model fields (matches actual DB schema)
PATIENT_ALLOWED_FIELDS = {
    'name',
    'phone', 
    'national_id',
    'first_visit_date',
    'created_at',
    'updated_at',
    'payment_type',
    'lifetime_value_score'
}

# Known invalid/legacy fields to explicitly reject
PATIENT_REJECTED_FIELDS = {
    'family',
    'mobile',
    'first_name',
    'last_name',
    'gender',
    'email',
    'address'
}


def sanitize_patient_data(data: dict) -> dict:
    """
    Filter patient data dict to only include valid fields.
    
    This is the CHOKE POINT for all Patient instantiation.
    Removes any fields that don't exist in the Patient model schema.
    
    Args:
        data: Raw dict that may contain invalid keys like 'family' or 'mobile'
        
    Returns:
        Sanitized dict with only valid Patient fields
    """
    if not isinstance(data, dict):
        return {}
    
    # First, filter to only allowed fields
    clean_data = {k: v for k, v in data.items() if k in PATIENT_ALLOWED_FIELDS}
    
    # Explicitly drop known bad fields (belt and suspenders)
    for bad_key in PATIENT_REJECTED_FIELDS:
        clean_data.pop(bad_key, None)
    
    return clean_data


def build_patient_from_dict(data: dict, **kwargs):
    """
    Build Patient instance with automatic data sanitization.
    
    This is the SINGLE POINT OF ENTRY for creating patients from dicts.
    ALL import/parsing code should use this function.
    
    Usage:
        patient = build_patient_from_dict({"name": "...", "phone": "..."})
        patient = build_patient_from_dict(raw_data, name="override")
    
    Args:
        data: Dict with patient data (may contain invalid keys like 'family', 'mobile')
        **kwargs: Additional keyword arguments (override data dict)
        
    Returns:
        Patient instance
    """
    from models import Patient
    
    # Merge data dict with kwargs (kwargs take priority)
    merged = {**data, **kwargs}
    
    # Sanitize to remove invalid fields
    clean_data = sanitize_patient_data(merged)
    
    # Create Patient with only valid fields
    return Patient(**clean_data)


def create_patient_safe(data: dict, **kwargs):
    """
    Alias for build_patient_from_dict for backward compatibility.
    """
    return build_patient_from_dict(data, **kwargs)
