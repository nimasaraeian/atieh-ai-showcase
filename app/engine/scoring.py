# -*- coding: utf-8 -*-
"""
Scheduling engine scoring functions (v1).

All individual scores and the total composite score are in [0.0, 1.0].

Public API
----------
calculate_urgency_score        – how urgently a treatment is needed
calculate_financial_score      – how financially favourable an insurer is
calculate_availability_score   – how many doctors are available for a slot
calculate_complexity_fit_score – how well a procedure's complexity fits a shift
calculate_total_score          – weighted composite of the four sub-scores
score_slot                     – compute all sub-scores for a single slot dict
DataStore                      – container for the four CSV catalogs
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def _has_persian(s: str) -> bool:
    return any("\u0600" <= c <= "\u06FF" for c in s or "")


def is_persian(text: str) -> bool:
    """Return True if text contains any Persian/Arabic characters in \\u0600-\\u06FF."""
    return _has_persian(text or "")


def normalize_doctor_name(text: str) -> str:
    """Re-export from app.utils.doctor_name for matching."""
    from app.utils.doctor_name import normalize_doctor_name as _impl
    return _impl(text)


def _build_doctor_name_map(doctor_shifts_rows) -> dict[str, str]:
    """
    Build doctor_id -> Persian doctor_name map from doctor_shifts rows.
    Expects rows like dicts with keys: doctor_id, doctor_name (or doctor_name_raw).
    """
    m: dict[str, str] = {}
    for r in doctor_shifts_rows or []:
        did = r.get("doctor_id")
        name = (r.get("doctor_name") or r.get("doctor_name_raw") or "").strip()
        if did is not None and name:
            m[str(did)] = name
    return m


def enforce_persian_doctor_names_in_slots(
    data: Dict[str, Any],
    doctor_ref_map: Optional[Dict[str, str]] = None,
) -> None:
    """
    Patch recommended_slots so doctor_name is always Persian.
    Uses doctor_ref_map (doctor_id -> Persian name) from reference loader.
    Modifies data in-place.
    """
    if doctor_ref_map is None:
        doctor_ref_map = {}

    # Build normalized_name -> persian_full_name for fallback when doctor_id not in map
    norm_to_persian: Dict[str, str] = {}
    for persian_name in doctor_ref_map.values():
        if persian_name and is_persian(persian_name):
            norm = normalize_doctor_name(persian_name)
            if norm:
                norm_to_persian[norm] = persian_name

    slots = data.get("recommended_slots", []) if isinstance(data, dict) else []
    for slot in slots:
        dn = (slot.get("doctor_name") or "").strip()
        did = str(slot.get("doctor_id") or "").strip()

        # 1. If doctor_id in ref map, use it
        if did and did in doctor_ref_map:
            slot["doctor_name"] = doctor_ref_map[did]
            continue

        # 2. If doctor_name already Persian, keep it
        if dn and is_persian(dn):
            continue

        # 3. Try resolve by normalized name match
        if dn:
            norm = normalize_doctor_name(dn)
            if norm and norm in norm_to_persian:
                slot["doctor_name"] = norm_to_persian[norm]
                continue

        # 4. Fallback
        slot["doctor_name"] = "دکتر نامشخص"


# ── Weights ────────────────────────────────────────────────────────────────────
# Must match Config.WEIGHT_* and the test assertions in tests/test_scoring.py.
# Updated to include a small time preference component.
_W_URGENCY         = 0.30
_W_FINANCIAL       = 0.25
_W_AVAILABILITY    = 0.20
_W_COMPLEXITY_FIT  = 0.15
_W_TIME            = 0.10


# ── Individual scoring functions ───────────────────────────────────────────────

def calculate_urgency_score(
    backlog_title: Optional[str],
    unfinished_treatments_df: pd.DataFrame,
    default: float = 0.5,
) -> float:
    """
    Return the urgency_weight for *backlog_title* from the unfinished-treatments
    catalog, or *default* (0.5) when the treatment is not found.

    Args:
        backlog_title:           Treatment / backlog name to look up.
        unfinished_treatments_df: DataFrame with at least the columns
                                  ``backlog_title`` and ``urgency_weight``.
        default:                 Fall-back value when no match is found.
    """
    if not backlog_title:
        return default
    if unfinished_treatments_df is None or unfinished_treatments_df.empty:
        return default
    if 'backlog_title' not in unfinished_treatments_df.columns:
        return default

    try:
        from app.utils.fa_normalize import normalize_fa
        needle = normalize_fa(backlog_title)
        for _, row in unfinished_treatments_df.iterrows():
            if normalize_fa(str(row['backlog_title'])) == needle:
                return float(row.get('urgency_weight', default))
    except Exception as exc:
        logger.warning(f"calculate_urgency_score: lookup error – {exc}")

    return default


def calculate_financial_score(
    insurance_name: Optional[str],
    insurance_priority_df: pd.DataFrame,
    default: float = 0.5,
) -> float:
    """
    Return the priority_score for *insurance_name* from the insurance-priority
    catalog, or *default* (0.5) when the insurer is not found.

    Args:
        insurance_name:      Insurance provider name.
        insurance_priority_df: DataFrame with at least the columns
                               ``insurance_name`` and ``priority_score``.
        default:             Fall-back value when no match is found.
    """
    if not insurance_name:
        return default
    if insurance_priority_df is None or insurance_priority_df.empty:
        return default
    if 'insurance_name' not in insurance_priority_df.columns:
        return default

    try:
        from app.utils.fa_normalize import normalize_fa
        needle = normalize_fa(insurance_name)
        for _, row in insurance_priority_df.iterrows():
            if normalize_fa(str(row['insurance_name'])) == needle:
                return float(row.get('priority_score', default))
    except Exception as exc:
        logger.warning(f"calculate_financial_score: lookup error – {exc}")

    return default


def calculate_availability_score(
    weekday: str,
    shift_code: str,
    doctor_shifts_df: pd.DataFrame,
    no_doctor_score: float = 0.3,
) -> float:
    """
    Score based on how many doctors are scheduled for *weekday* / *shift_code*.

    Scoring table:
      ≥3 doctors  →  0.90
       2 doctors  →  0.75
       1 doctor   →  0.60
       0 doctors  →  *no_doctor_score* (0.30)

    Args:
        weekday:          Persian weekday string (e.g. 'شنبه').
        shift_code:       'D', 'E', or 'N'.
        doctor_shifts_df: DataFrame with columns ``weekday_fa``, ``shift_code``,
                          ``doctor_name_norm``.
        no_doctor_score:  Returned when no doctor is available (0.3 per spec).
    """
    if doctor_shifts_df is None or doctor_shifts_df.empty:
        return no_doctor_score

    needed = {'weekday_fa', 'shift_code', 'doctor_name_norm'}
    if not needed.issubset(doctor_shifts_df.columns):
        return no_doctor_score

    logger.debug(
        "calculate_availability_score: received weekday=%r, shift_code=%r",
        weekday,
        shift_code,
    )

    try:
        from app.utils.fa_normalize import normalize_fa

        # Normalize weekday input (None/empty → no weekday filtering)
        weekday_norm: Optional[str] = None
        if weekday is not None:
            w = str(weekday).strip()
            if w:
                weekday_norm = normalize_fa(w)

        # Normalize weekday column in doctor_shifts_df for robust comparison
        doctor_shifts_df['weekday_norm'] = (
            doctor_shifts_df['weekday_fa']
            .astype(str)
            .map(normalize_fa)
        )

        unique_weekdays = (
            doctor_shifts_df['weekday_norm']
            .dropna()
            .astype(str)
            .unique()
            .tolist()[:10]
        )
        logger.debug(
            "calculate_availability_score: available weekdays (normalized, first 10)=%s",
            unique_weekdays,
        )

        mask = (doctor_shifts_df['shift_code'] == shift_code)
        if weekday_norm is not None:
            mask &= (doctor_shifts_df['weekday_norm'] == weekday_norm)

    except Exception as exc:
        # Fallback to raw comparison if normalization fails for any reason.
        logger.warning(
            "calculate_availability_score: normalization error – %s",
            exc,
        )
        unique_weekdays = (
            doctor_shifts_df['weekday_fa']
            .dropna()
            .astype(str)
            .unique()
            .tolist()[:10]
        )
        logger.debug(
            "calculate_availability_score: available weekdays (raw, first 10)=%s",
            unique_weekdays,
        )
        mask = (
            (doctor_shifts_df['weekday_fa'] == weekday) &
            (doctor_shifts_df['shift_code'] == shift_code)
        )

    n = len(doctor_shifts_df[mask])
    logger.debug(
        "calculate_availability_score: matched_rows=%d",
        n,
    )

    if n >= 3:
        return 0.90
    elif n == 2:
        return 0.75
    elif n == 1:
        return 0.60
    else:
        return no_doctor_score


def calculate_time_score(
    weekday: str,
    shift_code: str,
    start_time: str,
) -> float:
    """
    Time preference score in [0, 1], with a **soft** preference for earlier slots.

    Design goals:
      - Morning slots are still slightly preferred.
      - Scores are noticeably **flatter** across valid business hours so that
        08:00 does not heavily dominate 08:30 / 09:00 / 10:00.

    Implementation:
      - Compute a linear position of start_time within the shift window.
      - Map earliest → 1.0 and latest → 0.0 (as before).
      - Then compress the dynamic range to [0.6, 1.0] so time_score becomes
        a gentle nudge instead of a dominating factor.

    When parsing fails, we return a neutral 0.7.
    """
    try:
        from app.engine.time_blocks import SHIFT_BLOCKS_MINUTES
        from datetime import datetime

        if shift_code not in SHIFT_BLOCKS_MINUTES:
            return 0.7

        span_start, span_end = SHIFT_BLOCKS_MINUTES[shift_code]
        span = max(1, span_end - span_start)

        # Parse "HH:MM" into minutes
        t = datetime.strptime(str(start_time), "%H:%M").time()
        t_min = t.hour * 60 + t.minute
        # Clamp to [span_start, span_end]
        t_min = max(span_start, min(span_end, t_min))

        # Earlier is better: 1.0 at earliest, 0.0 at latest (raw linear score)
        raw = 1.0 - (t_min - span_start) / span
        raw = max(0.0, min(1.0, raw))

        # Compress into [0.6, 1.0] so that time preference is softer.
        # Example: earliest=1.0, mid-shift≈0.8, latest≈0.6.
        base = 0.6
        amplitude = 0.4
        return base + amplitude * raw
    except Exception:
        return 0.7


def calculate_complexity_fit_score(
    shift_code: str,
    service_complexity: float,
) -> float:
    """
    Score for how well a procedure's complexity fits a given shift.

    Night shift penalises high-complexity procedures:
      shift D (day):   0.60 + 0.40 × (1 − complexity × 0.30)  – best fit
      shift E (eve):   0.50 + 0.40 × (1 − complexity × 0.50)  – slight penalty
      shift N (night): min(0.75, 0.50 × (1 − complexity))     – strong penalty

    This ensures:
      calculate_complexity_fit_score('N', 0.9)  < 0.80   (test requirement)
      All return values are in [0, 1].
    """
    c = max(0.0, min(1.0, service_complexity))

    if shift_code == 'D':
        return min(1.0, 0.60 + 0.40 * (1.0 - c * 0.30))
    elif shift_code == 'E':
        return min(1.0, 0.50 + 0.40 * (1.0 - c * 0.50))
    else:   # 'N' or anything else
        return min(0.75, 0.50 * (1.0 - c))


def calculate_total_score(
    urgency_score: float,
    financial_score: float,
    availability_score: float,
    complexity_fit_score: float,
    time_score: float,
) -> float:
    """
    Weighted composite of the five sub-scores, clamped to [0, 1].
    
    Weights:
      urgency:         30 %   (_W_URGENCY)
      financial:       25 %   (_W_FINANCIAL)
      availability:    20 %   (_W_AVAILABILITY)
      complexity_fit:  15 %   (_W_COMPLEXITY_FIT)
      time:            10 %   (_W_TIME)
    """
    total = (
        _W_URGENCY        * urgency_score +
        _W_FINANCIAL      * financial_score +
        _W_AVAILABILITY   * availability_score +
        _W_COMPLEXITY_FIT * complexity_fit_score +
        _W_TIME           * time_score
    )
    return max(0.0, min(1.0, total))


def calculate_weighted_components(
    urgency_score: float,
    financial_score: float,
    availability_score: float,
    complexity_fit_score: float,
    time_score: float,
) -> Dict[str, float]:
    """
    Return weighted components that sum to total_base (clamped).
    This enables explainable scoring without changing ranking behavior.
    """
    comps = {
        "urgency":        _W_URGENCY        * urgency_score,
        "financial":      _W_FINANCIAL      * financial_score,
        "availability":   _W_AVAILABILITY   * availability_score,
        "complexity_fit": _W_COMPLEXITY_FIT * complexity_fit_score,
        "time":           _W_TIME           * time_score,
    }
    total_base = sum(comps.values())
    total_base = max(0.0, min(1.0, total_base))
    comps["total_base"] = total_base
    return comps


# ── Slot-level scoring ─────────────────────────────────────────────────────────

def score_slot(
    slot: Dict[str, Any],
    service_info: Optional[Dict[str, Any]],
    request_params: Dict[str, Any],
    data_store: "DataStore",
) -> Dict[str, Any]:
    """
    Compute all four sub-scores plus the composite total for a single slot.

    Args:
        slot:           Dict with keys ``weekday``, ``shift_code``, ``start_time``,
                        ``end_time``.
        service_info:   Dict from ``DataStore.get_service_info()``; may be None.
        request_params: Dict from the CRM / API request.  Relevant keys:
                        ``insurance_name``, ``backlog_title``.
        data_store:     Loaded :class:`DataStore` instance.

    Returns:
        Dict with keys: ``slot``, ``urgency_score``, ``financial_score``,
        ``availability_score``, ``complexity_fit_score``, ``total_score``,
        ``service_complexity``.
    """
    si               = service_info or {}
    service_complexity = float(si.get('complexity_weight', 0.5))

    insurance_name = request_params.get('insurance_name')
    backlog_title  = request_params.get('backlog_title')
    weekday        = slot.get('weekday', '')
    shift_code     = slot.get('shift_code', 'D')
    start_time     = slot.get('start_time', '')

    urgency_score        = calculate_urgency_score(
        backlog_title, data_store.unfinished_treatments
    )
    financial_score      = calculate_financial_score(
        insurance_name, data_store.insurance_priority
    )
    availability_score   = calculate_availability_score(
        weekday, shift_code, data_store.doctor_shifts
    )
    complexity_fit_score = calculate_complexity_fit_score(
        shift_code, service_complexity
    )
    time_score           = calculate_time_score(
        weekday, shift_code, start_time
    )
    # Explainable components (base)
    comps = calculate_weighted_components(
        urgency_score, financial_score, availability_score, complexity_fit_score, time_score
    )
    total_base = comps["total_base"]

    # Preferred doctor boost: handled at recommendation level (after doctor_id is assigned).
    preferred_doctor_match = False
    preferred_doctor_boost = 0.0

    total_score = total_base

    # finalize components
    comps["preferred_doctor_boost"] = preferred_doctor_boost
    comps["total"] = total_score

    return {
        'slot':                   slot,
        'urgency_score':          urgency_score,
        'financial_score':        financial_score,
        'availability_score':     availability_score,
        'complexity_fit_score':   complexity_fit_score,
        'time_score':             time_score,
        'total_score':            total_score,
        'total_base':             total_base,
        'preferred_doctor_match': preferred_doctor_match,
        'preferred_doctor_boost': preferred_doctor_boost,
        'components':             comps,
        'service_complexity':     service_complexity,
    }


# ── DataStore ──────────────────────────────────────────────────────────────────

class DataStore:
    """
    Central data store for the scheduling engine.

    Loads the four CSV catalogs produced by ``app/loaders/atieh_loader.py``
    and exposes lookup helpers used by scoring and recommendation functions.

    Attributes:
        doctor_shifts:          DataFrame – weekday_fa / shift_code / doctor_name_norm
        services_catalog:       DataFrame – service_name / default_duration_min / complexity_weight
        unfinished_treatments:  DataFrame – backlog_title / urgency_weight
        insurance_priority:     DataFrame – insurance_name / priority_score
    """

    def __init__(self) -> None:
        from app.config import Config
        self.data_dir = Config.DATA_DIR
        self.doctor_shifts:          pd.DataFrame = pd.DataFrame()
        self.services_catalog:       pd.DataFrame = pd.DataFrame()
        self.unfinished_treatments:  pd.DataFrame = pd.DataFrame()
        self.insurance_priority:     pd.DataFrame = pd.DataFrame()
        try:
            from app.loaders.reference_doctors import load_doctors_reference
            self.doctor_ref_map, self.doctor_norm_map = load_doctors_reference(base_dir="data/inputs/reference")
        except Exception as exc:
            logger.warning("DataStore: could not load reference doctors – %s", exc)
            self.doctor_ref_map = {}
            self.doctor_norm_map = {}
        try:
            from app.loaders.doctors_reference_csv import load_doctors_reference_csv
            self.doctors_ref = load_doctors_reference_csv(self.data_dir)
            self.doctor_ref_by_norm = {d.doctor_name_norm: d for d in self.doctors_ref}
        except Exception as exc:
            logger.warning("DataStore: could not load doctors_reference_csv – %s", exc)
            self.doctors_ref = []
            self.doctor_ref_by_norm = {}

    # ── Loading ───────────────────────────────────────────────────────────────

    def load_from_csv(
        self,
        doctor_shifts_path:          Optional[Path] = None,
        services_catalog_path:       Optional[Path] = None,
        unfinished_treatments_path:  Optional[Path] = None,
        insurance_priority_path:     Optional[Path] = None,
    ) -> None:
        """
        Load all four CSV catalogs.  Paths default to the locations defined in
        :class:`app.config.Config`.  Missing files are logged as warnings and
        result in empty DataFrames (non-fatal).

        When the first positional arg is a directory path (e.g. "data/outputs"),
        uses it as base dir and loads base/doctor_shifts.csv, etc.

        Fix F: Permission denied on outputs dir is treated as optional – uses
        empty DataFrames instead of failing.
        """
        from app.config import Config

        base = None
        if doctor_shifts_path is not None:
            p = Path(doctor_shifts_path)
            if p.is_dir():
                base = p
                doctor_shifts_path = base / "doctor_shifts.csv"
                services_catalog_path = base / "services_catalog.csv"
                unfinished_treatments_path = base / "unfinished_treatments.csv"
                insurance_priority_path = base / "insurance_priority.csv"

        path_map = {
            'doctor_shifts':         doctor_shifts_path         or Config.DOCTOR_SHIFTS_CSV,
            'services_catalog':      services_catalog_path      or Config.SERVICES_CATALOG_CSV,
            'unfinished_treatments': unfinished_treatments_path or Config.UNFINISHED_TREATMENTS_CSV,
            'insurance_priority':    insurance_priority_path    or Config.INSURANCE_PRIORITY_CSV,
        }

        for attr, path in path_map.items():
            path = Path(path)
            try:
                if path.is_dir():
                    logger.warning(
                        f"DataStore: '{path.name}' is a directory – skipping "
                        f"(use directory as base or provide file path)"
                    )
                    continue
                df = pd.read_csv(path, encoding='utf-8-sig')
                setattr(self, attr, df)
                logger.info(f"DataStore: loaded {len(df)} rows from '{path.name}'")
            except FileNotFoundError:
                logger.warning(
                    f"DataStore: '{path.name}' not found – using empty DataFrame "
                    f"(run app/loaders to generate CSV catalogs)"
                )
            except (PermissionError, OSError) as exc:
                logger.warning(
                    f"DataStore: permission/access error for '{path.name}' – "
                    f"using empty DataFrame: {exc}"
                )
            except Exception as exc:
                logger.error(f"DataStore: error loading '{path.name}': {exc}")

    # ── Lookup helpers ────────────────────────────────────────────────────────

    def get_service_info(self, service_key: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Return a dict with catalog metadata for *service_key*, or ``None``.

        Accepts:
        - service_id: e.g. TREATMENT_5 → 5th row in catalog (1-indexed)
        - Persian title: exact normalized match, or fuzzy (catalog item
          starts with query / query is prefix of catalog item)
        """
        if not service_key or self.services_catalog.empty:
            return None
        if 'service_name' not in self.services_catalog.columns:
            return None

        try:
            import re
            from app.utils.fa_normalize import normalize_fa

            # 1. service_id lookup (e.g. TREATMENT_5)
            m = re.match(r"^TREATMENT_(\d+)$", str(service_key).strip(), re.I)
            if m:
                idx = int(m.group(1))
                if 1 <= idx <= len(self.services_catalog):
                    row = self.services_catalog.iloc[idx - 1]
                    return row.to_dict()
                return None

            # 2. Persian title: exact match first
            needle = normalize_fa(service_key)
            for _, row in self.services_catalog.iterrows():
                catalog_norm = normalize_fa(str(row['service_name']))
                if catalog_norm == needle:
                    return row.to_dict()

            # 3. Fuzzy: catalog item starts with query, or query contained in catalog
            for _, row in self.services_catalog.iterrows():
                catalog_norm = normalize_fa(str(row['service_name']))
                if catalog_norm.startswith(needle) or needle in catalog_norm:
                    return row.to_dict()

        except Exception as exc:
            logger.warning(f"DataStore.get_service_info: lookup error – {exc}")

        return None

    def get_doctors_for_slot(self, weekday: str, shift_code: str) -> List[str]:
        """
        Return the list of normalised doctor names scheduled for *weekday* /
        *shift_code*.  Returns an empty list when no data is available.
        """
        if self.doctor_shifts.empty:
            return []

        needed = {'weekday_fa', 'shift_code', 'doctor_name_norm'}
        if not needed.issubset(self.doctor_shifts.columns):
            return []

        try:
            from app.utils.fa_normalize import normalize_fa

            weekday_norm: Optional[str] = None
            if weekday is not None:
                w = str(weekday).strip()
                if w:
                    weekday_norm = normalize_fa(w)

            # Normalize weekday column once for comparison
            self.doctor_shifts['weekday_norm'] = (
                self.doctor_shifts['weekday_fa']
                .astype(str)
                .map(normalize_fa)
            )

            mask = (self.doctor_shifts['shift_code'] == shift_code)
            if weekday_norm is not None:
                mask &= (self.doctor_shifts['weekday_norm'] == weekday_norm)

        except Exception as exc:
            logger.warning(
                "DataStore.get_doctors_for_slot: normalization error – %s",
                exc,
            )
            mask = (
                (self.doctor_shifts['weekday_fa'] == weekday) &
                (self.doctor_shifts['shift_code'] == shift_code)
            )

        return [
            d for d in self.doctor_shifts.loc[mask, 'doctor_name_norm']
                                          .dropna().unique().tolist()
            if d
        ]

    def resolve_shift_doctor_to_reference(self, shift_doctor_name: str) -> Optional[tuple[str, str]]:
        """
        Resolve a shift doctor name (e.g. "بهزاد" from doctor_shifts) to reference.
        Returns (doctor_id, doctor_name_display) or None.
        """
        from app.loaders.reference_doctors import resolve_shift_name_to_reference
        return resolve_shift_name_to_reference(shift_doctor_name, getattr(self, "doctor_norm_map", {}))
