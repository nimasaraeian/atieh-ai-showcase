# -*- coding: utf-8 -*-
"""Execute engine job and load results from per-request output directory."""
import logging
import uuid
from pathlib import Path

import pandas as pd

from app.engine.run_engine import run_engine_job

logger = logging.getLogger(__name__)
OUTPUT_ROOT = Path("data/outputs/runs")


def normalize_opt(value):
    """Normalize optional string-like fields for engine invocation."""
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        return stripped
    return value


def _nan_to_null(obj):
    """Convert NaN/NaT to None for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _nan_to_null(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_nan_to_null(v) for v in obj]
    if pd.isna(obj):
        return None
    return obj


def _df_to_records(df: pd.DataFrame) -> list:
    """Convert DataFrame to list of dicts with NaN -> null."""
    records = df.where(pd.notnull(df), None).to_dict(orient="records")
    return [_nan_to_null(r) for r in records]


def _count_preferred_matches(df: pd.DataFrame) -> int:
    """Count rows where preferred_doctor_match is True."""
    if "preferred_doctor_match" not in df.columns:
        return 0
    col = df["preferred_doctor_match"]
    return int((col.astype(str).str.lower() == "true").sum())


def run_engine_and_load_results(
    *,
    service: str,
    insurance: str | None,
    backlog: str | None,
    doctor: int | None,
    weekday: str | None,
) -> dict:
    import time
    # Normalize optional inputs to avoid passing empty/None-like values into the engine.
    norm_insurance = normalize_opt(insurance)
    norm_backlog = normalize_opt(backlog)
    norm_weekday = normalize_opt(weekday)

    run_id = uuid.uuid4().hex[:12]
    out_dir = OUTPUT_ROOT / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    engine_kwargs: dict = {
        "service": service,
        "out_dir": str(out_dir),
    }
    if norm_insurance is not None:
        engine_kwargs["insurance"] = norm_insurance
    if norm_backlog is not None:
        engine_kwargs["backlog"] = norm_backlog
    if doctor is not None:
        engine_kwargs["doctor"] = doctor
    if norm_weekday is not None:
        engine_kwargs["weekday"] = norm_weekday

    logger.info("Running engine job with args: %s", engine_kwargs)

    t0 = time.perf_counter()
    run_engine_job(**engine_kwargs)
    elapsed = time.perf_counter() - t0
    logger.info("run_id=%s engine_executed_ms=%.0f", run_id, elapsed * 1000)

    rec_path = out_dir / "slot_recommendations.csv"
    draft_path = out_dir / "schedule_draft.csv"

    if not rec_path.exists():
        raise FileNotFoundError(f"Missing output file: {rec_path}")

    rec_df = pd.read_csv(rec_path, encoding="utf-8-sig")
    recs = _df_to_records(rec_df)

    draft: dict = {}
    if draft_path.exists():
        draft_df = pd.read_csv(draft_path, encoding="utf-8-sig")
        if len(draft_df):
            draft = _df_to_records(draft_df)[0]

    preferred_matches = _count_preferred_matches(rec_df)

    return {
        "run_id": run_id,
        "input": {
            "service": service,
            "insurance": insurance,
            "backlog": backlog,
            "doctor": doctor,
            "weekday": weekday,
        },
        "draft": draft,
        "recommendations": recs,
        "counts": {
            "recommendations": len(recs),
            "preferred_matches": preferred_matches,
        },
    }