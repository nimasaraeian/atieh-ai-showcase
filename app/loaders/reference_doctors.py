# -*- coding: utf-8 -*-
"""
Reference doctors loader – single source of truth for doctor_id -> Persian name mapping.

Loads doctors_reference.csv (canonical) and doctors.csv (legacy compat).
Tolerant: missing folder or files -> empty map + log warning (does not crash).

Maps built:
  - doctor_ref_map: doctor_id -> doctor_name_display
  - doctor_norm_map: doctor_name_norm -> {doctor_id, doctor_name_display, specialty}
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

ID_COLUMNS = ("doctor_id", "id", "code", "physician_id")
NAME_COLUMNS = ("doctor_name", "name_fa", "full_name", "نام", "پزشک", "doctor_name_display")


def _norm_for_match(s: str) -> str:
    """Normalize for matching: ی/ي, ک/ك, strip, collapse space."""
    s = (s or "").strip()
    s = s.replace("ي", "ی").replace("ك", "ک").replace("\u200c", " ")
    return " ".join(s.split())


def load_reference_doctors(base_dir: str | Path = "data/inputs/reference") -> Dict[str, str]:
    """Return doctor_id -> doctor_name_display. Uses load_doctors_reference."""
    ref_map, _ = load_doctors_reference(base_dir)
    return ref_map


def _load_one(result: Dict[str, str], path: Path) -> None:
    """Load one CSV file and merge into result. Excel files are skipped (no scan)."""
    import pandas as pd

    if path.suffix.lower() != ".csv":
        return  # Skip Excel and other formats
    df = pd.read_csv(path, encoding="utf-8-sig")

    if df.empty:
        return

    cols = [c for c in df.columns if c and isinstance(c, str)]
    id_col = next((c for c in ID_COLUMNS if c in cols), None)
    name_col = next((c for c in NAME_COLUMNS if c in cols), None)

    if not id_col or not name_col:
        logger.warning(
            "reference_doctors: '%s' missing id column (need one of %s) or name column (need one of %s)",
            path.name, ID_COLUMNS, NAME_COLUMNS,
        )
        return

    for _, row in df.iterrows():
        did = row.get(id_col)
        name = row.get(name_col)
        if did is None or pd.isna(did) or name is None or pd.isna(name):
            continue
        did_str = str(int(did) if isinstance(did, float) and did == int(did) else did).strip()
        name_str = str(name).strip()
        if did_str and name_str:
            result[did_str] = name_str


def load_doctors_reference(
    base_dir: str | Path = "data/inputs/reference",
) -> tuple[Dict[str, str], Dict[str, Dict[str, Any]]]:
    """
    Load doctors_reference.csv and build:
      - doctor_ref_map: doctor_id -> doctor_name_display
      - doctor_norm_map: doctor_name_norm -> {doctor_id, doctor_name_display, specialty}

    Returns:
        (doctor_ref_map, doctor_norm_map)
    """
    import pandas as pd

    base = Path(base_dir)
    ref_map: Dict[str, str] = {}
    norm_map: Dict[str, Dict[str, Any]] = {}

    # Prefer doctors_reference.csv (canonical format)
    ref_path = base / "doctors_reference.csv"
    if ref_path.exists():
        try:
            df = pd.read_csv(ref_path, encoding="utf-8-sig")
            for _, row in df.iterrows():
                did = row.get("doctor_id")
                display = row.get("doctor_name_display")
                norm = row.get("doctor_name_norm")
                specialty = row.get("specialty", "")
                if did is None or pd.isna(did):
                    continue
                did_str = str(int(did) if isinstance(did, float) and did == int(did) else did).strip()
                display_str = (str(display).strip() if display is not None and not pd.isna(display) else "")
                norm_str = (str(norm).strip() if norm is not None and not pd.isna(norm) else "").strip()
                if did_str:
                    ref_map[did_str] = display_str or f"دکتر {norm_str}" if norm_str else "دکتر نامشخص"
                if norm_str:
                    norm_map[_norm_key(norm_str)] = {
                        "doctor_id": did_str,
                        "doctor_name_display": display_str or f"دکتر {norm_str}",
                        "specialty": str(specialty).strip() if specialty is not None and not pd.isna(specialty) else "",
                    }
        except Exception as exc:
            logger.warning("reference_doctors: error loading doctors_reference.csv – %s", exc)

    # Merge doctors.csv (legacy: 101, 102, 103) into ref_map only
    # Only load known CSV files – no Excel scan (avoids WARNING for xlsx in reference)
    for name in ("doctors.csv",):
        path = base / name
        if not path.exists():
            continue
        try:
            _load_one(ref_map, path)
            # Add legacy ids to norm_map for shift resolution
            for did_str, display in list(ref_map.items()):
                if did_str not in {v["doctor_id"] for v in norm_map.values()}:
                    norm = _strip_dr(display)
                    if norm:
                        norm_map[_norm_key(norm)] = {
                            "doctor_id": did_str,
                            "doctor_name_display": display,
                            "specialty": "",
                        }
        except Exception as exc:
            logger.warning("reference_doctors: error loading '%s' – %s", path.name, exc)

    return (ref_map, norm_map)


def _norm_key(s: str) -> str:
    return _norm_for_match(s)


def _strip_dr(s: str) -> str:
    s = (s or "").strip()
    for p in ("دکتر ", "دكتر ", "دکتر", "دكتر"):
        if s.startswith(p):
            return s[len(p):].strip()
    return s


def resolve_preferred_doctor_to_id(
    preferred_doctor: str,
    doctor_norm_map: Dict[str, Dict[str, Any]],
) -> Optional[str]:
    """
    Resolve preferred_doctor (user input) to doctor_id from reference.
    Match: exact norm key, or norm contains/ends-with preferred normalized.
    Returns doctor_id or None.
    """
    if not preferred_doctor or not doctor_norm_map:
        return None
    preferred_norm = _norm_for_match(_strip_dr(preferred_doctor))
    if not preferred_norm:
        return None
    if preferred_norm in doctor_norm_map:
        return doctor_norm_map[preferred_norm]["doctor_id"]
    for ref_norm, r in doctor_norm_map.items():
        if ref_norm == preferred_norm:
            return r["doctor_id"]
        if preferred_norm in ref_norm or ref_norm.endswith(preferred_norm) or ref_norm.endswith(" " + preferred_norm):
            return r["doctor_id"]
    return None


def resolve_shift_name_to_reference(
    shift_doctor_name: str,
    doctor_norm_map: Dict[str, Dict[str, Any]],
) -> Optional[tuple[str, str]]:
    """
    Resolve a shift doctor name (e.g. "بهزاد" from doctor_shifts) to reference.
    Match: ref doctor_name_norm contains shift_name or ends with shift_name.

    Returns:
        (doctor_id, doctor_name_display) or None
    """
    if not shift_doctor_name or not doctor_norm_map:
        return None
    shift_norm = _norm_for_match(shift_doctor_name)
    if not shift_norm:
        return None
    # Exact key match
    if shift_norm in doctor_norm_map:
        r = doctor_norm_map[shift_norm]
        return (r["doctor_id"], r["doctor_name_display"])
    # Contains / ends-with: ref norm contains shift_norm or ends with shift_norm
    for ref_norm, r in doctor_norm_map.items():
        if ref_norm == shift_norm:
            return (r["doctor_id"], r["doctor_name_display"])
        if shift_norm in ref_norm or ref_norm.endswith(shift_norm) or ref_norm.endswith(" " + shift_norm):
            return (r["doctor_id"], r["doctor_name_display"])
    return None
