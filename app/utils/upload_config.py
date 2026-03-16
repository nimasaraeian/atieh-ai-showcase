from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.importers.common.paths import find_repo_root

UploadCategory = Literal["history", "payments", "reference"]


@dataclass(frozen=True)
class UploadPaths:
    base_dir: Path
    staging_dir: Path
    inputs_dir: Path
    history_dir: Path
    payments_dir: Path
    reference_dir: Path


def get_upload_paths() -> UploadPaths:
    """
    Centralized upload path config.

    - UPLOAD_BASE_DIR: absolute or relative path; defaults to <repo_root>/data
    - Keeps the existing importer-compatible structure under data/inputs/...
    """
    repo_root = find_repo_root()
    base_env = os.getenv("UPLOAD_BASE_DIR")
    base_dir = Path(base_env) if base_env else (repo_root / "data")
    if not base_dir.is_absolute():
        base_dir = (repo_root / base_dir).resolve()

    inputs_dir = base_dir / "inputs"
    staging_dir = base_dir / "uploads_staging"

    history_dir = inputs_dir / "history"
    payments_dir = inputs_dir / "payments"
    reference_dir = inputs_dir / "reference"

    return UploadPaths(
        base_dir=base_dir,
        staging_dir=staging_dir,
        inputs_dir=inputs_dir,
        history_dir=history_dir,
        payments_dir=payments_dir,
        reference_dir=reference_dir,
    )


def ensure_upload_dirs() -> UploadPaths:
    paths = get_upload_paths()
    for p in (
        paths.base_dir,
        paths.inputs_dir,
        paths.staging_dir,
        paths.history_dir,
        paths.payments_dir,
        paths.reference_dir,
    ):
        p.mkdir(parents=True, exist_ok=True)
    return paths


def category_to_target_dir(category: UploadCategory) -> Path:
    paths = get_upload_paths()
    if category == "history":
        return paths.history_dir
    if category == "payments":
        return paths.payments_dir
    return paths.reference_dir

