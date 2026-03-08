# -*- coding: utf-8 -*-
"""
Frontend-friendly API endpoints used by the web UI.

These routes expose simplified catalog and search APIs on the root path
so that any frontend (Next.js, static UI, etc.) can call them directly:

- GET /treatment-types
- GET /payment-types
- GET /patients
- GET /appointments
"""
from __future__ import annotations

import logging
import os
from typing import List, Optional, Dict

import pandas as pd
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db
from models import Patient, PaymentType, TreatmentType

router = APIRouter(tags=["frontend"])
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Helpers for resolving normalized catalog sources
# ------------------------------------------------------------------------------


def _to_universal_items(items: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Normalize catalog items to universal shape:
      { id, value, label, name }
    """
    normalized: List[Dict[str, str]] = []
    for item in items:
        # Preserve previous id/label as primary source
        raw_id = item.get("id") or ""
        raw_label = item.get("label") or ""

        _id = str(raw_id or raw_label)
        _label = str(raw_label or _id)

        normalized.append(
            {
                "id": _id,
                "value": _id,
                "label": _label,
                "name": _label,
            }
        )
    return normalized


def _load_services_from_db(db: Session) -> Optional[List[Dict[str, str]]]:
    """
    Try to load services catalog from a normalized DB table/view.

    Returns list of dicts or None if no suitable table/view is found.
    """
    # Common normalized table/view names
    candidates = ["services_catalog", "v_services_catalog"]

    for table in candidates:
        try:
            exists = db.execute(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type IN ('table','view') AND name = :name"
                ),
                {"name": table},
            ).fetchone()
            if not exists:
                continue

            rows = db.execute(
                text(
                    f"SELECT service_name, "
                    f"COALESCE(service_name_norm, service_name) AS service_id "
                    f"FROM {table}"
                )
            ).fetchall()
            items: List[Dict[str, str]] = []
            for service_name, service_id in rows:
                if not service_name or not service_id:
                    continue
                sid = str(service_id)
                name = str(service_name)
                items.append(
                    {
                        "id": sid,
                        "label": name,
                        "value": sid,
                        "name": name,
                    }
                )
            logger.info(
                "treatment_types: loaded %d rows from DB table/view '%s'",
                len(items),
                table,
            )
            return items
        except Exception as exc:
            logger.warning(
                "treatment_types: error reading DB table '%s': %s", table, exc
            )

    return None


def _resolve_services_catalog_path() -> Optional[str]:
    """
    Return the first existing path for services catalog CSV, or None.

    Priority:
      1) data/outputs/services_catalog.csv  (normalized layer)
      2) data/inputs/reference/services_catalog.csv
      3) data/reference/services_catalog.csv
    """
    candidate_paths = [
        "data/outputs/services_catalog.csv",
        "data/inputs/reference/services_catalog.csv",
        "data/reference/services_catalog.csv",
    ]
    for path in candidate_paths:
        if os.path.exists(path):
            return path
    return None


def _load_insurance_from_db(db: Session, mode: str) -> Optional[List[Dict[str, str]]]:
    """
    Try to load insurance/payment catalog from normalized DB tables/views.
    
    Priority:
      1) stg_payments (payer_source_norm / insurer_name_norm)
      2) insurance_priority / v_insurance_priority
    """
    # 1) From staging payments (preferred – closest to real normalized source)
    try:
        exists = db.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type IN ('table','view') AND name = 'stg_payments'"
            )
        ).fetchone()
        if exists:
            # Mode: payer_source -> distinct payer_source_norm (cash / insurance / ...)
            if mode == "payer_source":
                rows = db.execute(
                    text(
                        "SELECT DISTINCT payer_source_norm "
                        "FROM stg_payments WHERE payer_source_norm IS NOT NULL"
                    )
                ).fetchall()
                items: List[Dict[str, str]] = []
                for (ps,) in rows:
                    ps_str = str(ps)
                    if ps_str == "insurance":
                        name = "بیمه"
                    elif ps_str == "cash":
                        name = "نقدی"
                    else:
                        name = ps_str
                    items.append(
                        {
                            "id": ps_str,
                            "value": ps_str,
                            "label": name,
                            "name": name,
                        }
                    )
                logger.info(
                    "payment_types: source=db(stg_payments, mode=payer_source) count=%d",
                    len(items),
                )
                return items

            # Mode: insurers -> distinct insurer_name_norm
            rows = db.execute(
                text(
                    "SELECT DISTINCT insurer_name_norm "
                    "FROM stg_payments WHERE insurer_name_norm IS NOT NULL"
                )
            ).fetchall()
            items = []
            for (ins,) in rows:
                name = str(ins)
                items.append(
                    {
                        "id": name,
                        "value": name,
                        "label": name,
                        "name": name,
                    }
                )
            logger.info(
                "payment_types: source=db(stg_payments, mode=insurers) count=%d",
                len(items),
            )
            return items
    except Exception as exc:
        logger.warning("payment_types: error reading stg_payments: %s", exc)

    # 2) Fallback to normalized insurance_priority table/view if present
    candidates = ["insurance_priority", "v_insurance_priority"]

    for table in candidates:
        try:
            exists = db.execute(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type IN ('table','view') AND name = :name"
                ),
                {"name": table},
            ).fetchone()
            if not exists:
                continue

            rows = db.execute(
                text(
                    f"SELECT "
                    f"COALESCE(insurer_name_norm, insurance_name) AS name "
                    f"FROM {table}"
                )
            ).fetchall()

            if mode == "payer_source":
                # We only know that this represents insurances, so expose a single generic 'insurance' payer.
                if rows:
                    name = "بیمه"
                    items = [
                        {
                            "id": "insurance",
                            "value": "insurance",
                            "label": name,
                            "name": name,
                        }
                    ]
                else:
                    items = []
                logger.info(
                    "payment_types: source=db(%s, mode=payer_source) count=%d",
                    table,
                    len(items),
                )
                return items

            # mode == insurers: return distinct insurer names
            items: List[Dict[str, str]] = []
            for (name,) in rows:
                if not name:
                    continue
                n = str(name)
                items.append(
                    {
                        "id": n,
                        "value": n,
                        "label": n,
                        "name": n,
                    }
                )
            logger.info(
                "payment_types: source=db(%s, mode=insurers) count=%d",
                table,
                len(items),
            )
            return items
        except Exception as exc:
            logger.warning(
                "payment_types: error reading DB table '%s': %s", table, exc
            )

    return None


def _resolve_insurance_priority_path() -> Optional[str]:
    """
    Return the first existing path for insurance/priority CSV, or None.

    Priority:
      1) data/outputs/insurance_priority.csv  (normalized layer)
      2) data/inputs/payments/insurance_payment_priority.csv
      3) data/inputs/payments/insurance_priority.csv
      4) data/reference/insurance_payment_priority.csv
      5) data/inputs/reference/insurance_payment_priority.csv
    """
    candidate_paths = [
        "data/outputs/insurance_priority.csv",
        "data/inputs/payments/insurance_payment_priority.csv",
        "data/inputs/payments/insurance_priority.csv",
        "data/reference/insurance_payment_priority.csv",
        "data/inputs/reference/insurance_payment_priority.csv",
    ]
    for path in candidate_paths:
        if os.path.exists(path):
            return path
    return None


@router.get("/treatment-types")
def treatment_types(db: Session = Depends(get_db)) -> List[dict]:
    """
    Return treatment catalog for dropdowns.

    Priority:
      a) Normalized DB table/view (services_catalog / v_services_catalog)
      b) Normalized CSV in data/outputs/services_catalog.csv
      c) Reference CSVs in data/inputs or data/reference
      d) Enum fallback

    Output format:
        [
          { "id": "...", "label": "...", "value": "...", "name": "..." },
          ...
        ]
    """
    # 1) Try DB normalized catalog
    db_items = _load_services_from_db(db)
    if db_items is not None:
        items = _to_universal_items(db_items)
        logger.info("treatment_types: returning %d items from DB (normalized)", len(items))
        return items

    # 2) Fall back to CSVs (normalized outputs first)
    csv_path = _resolve_services_catalog_path()
    if csv_path:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        if "service_name" in df.columns:
            id_col = (
                "service_name_norm"
                if "service_name_norm" in df.columns
                else "service_name"
            )
            df = df.dropna(subset=["service_name"]).drop_duplicates(subset=[id_col])
            raw_items: List[Dict[str, str]] = []
            for _, row in df.iterrows():
                service_id = str(row[id_col])
                name = str(row["service_name"])
                raw_items.append(
                    {
                        "id": service_id,
                        "label": name,
                    }
                )
            items = _to_universal_items(raw_items)
            logger.info(
                "treatment_types: source=csv('%s') count=%d",
                csv_path,
                len(items),
            )
            return items

    # 3) Enum fallback as last resort
    raw_items: List[dict] = []
    for t in TreatmentType:
        label = t.name.replace("_", " ")
        raw_items.append(
            {
                "id": t.name,  # e.g. "TREATMENT_1"
                "label": label,
            }
        )
    items = _to_universal_items(raw_items)
    logger.warning(
        "treatment_types: falling back to TreatmentType enum (%d items)", len(items)
    )
    return items


@router.get("/payment-types")
def payment_types(
    mode: str = Query("payer_source", description="payer_source or insurers"),
    db: Session = Depends(get_db),
) -> List[dict]:
    """
    Return payment/insurance catalog for dropdowns.

    mode:
      - payer_source (default): distinct payer_source_norm (cash / insurance / ...)
      - insurers: distinct insurer_name_norm (ایران، نیروهای مسلح، ...)

    Priority:
      a) Normalized DB table/view (stg_payments, insurance_priority / v_insurance_priority)
      b) Normalized CSV in data/outputs/insurance_priority.csv
      c) Reference CSVs in data/inputs/payments or data/reference
      d) Enum fallback

    Output format:
        [
          { "id": "...", "label": "...", "value": "...", "name": "..." },
          ...
        ]
    """
    mode_normalized = (mode or "payer_source").strip().lower()
    if mode_normalized not in {"payer_source", "insurers"}:
        mode_normalized = "payer_source"
    # 1) Try DB normalized catalog
    db_items = _load_insurance_from_db(db, mode_normalized)
    if db_items is not None:
        logger.info("payment_types: returning %d items from DB", len(db_items))
        return db_items

    # 2) Fall back to CSVs (normalized outputs first)
    csv_path = _resolve_insurance_priority_path()
    if csv_path:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        # Try to detect a suitable display/name column for insurers
        name_col = None
        for cand in ["insurer_name_norm", "insurance_name", "payer_source_norm"]:
            if cand in df.columns:
                name_col = cand
                break

        if name_col:
            df = df.dropna(subset=[name_col]).drop_duplicates(subset=[name_col])
            items: List[Dict[str, str]] = []

            if mode_normalized == "payer_source":
                # From CSV we only know about insurances; expose a generic 'insurance' payer if any rows exist.
                if not df.empty:
                    name = "بیمه"
                    items.append(
                        {
                            "id": "insurance",
                            "value": "insurance",
                            "label": name,
                            "name": name,
                        }
                    )
            else:  # insurers
                for _, row in df.iterrows():
                    name = str(row[name_col])
                    items.append(
                        {
                            "id": name,
                            "value": name,
                            "label": name,
                            "name": name,
                        }
                    )

            logger.info(
                "payment_types: source=csv('%s', mode=%s) count=%d",
                csv_path,
                mode_normalized,
                len(items),
            )
            return items

    # 3) Enum fallback as last resort
    items: List[dict] = []
    if mode_normalized == "payer_source":
        # Derive generic cash/insurance from enum values
        payer_sources: set[str] = set()
        for pt in PaymentType:
            if pt.value == "cash":
                payer_sources.add("cash")
            elif pt.value.startswith("insurance_"):
                payer_sources.add("insurance")
        for ps in sorted(payer_sources):
            if ps == "insurance":
                name = "بیمه"
            elif ps == "cash":
                name = "نقدی"
            else:
                name = ps
            items.append(
                {
                    "id": ps,
                    "value": ps,
                    "label": name,
                    "name": name,
                }
            )
    else:  # insurers
        for pt in PaymentType:
            value = pt.value
            if value.startswith("insurance_"):
                try:
                    num = int(value.split("_", 1)[1])
                    name = f"بیمه {num}"
                except Exception:
                    name = value
                items.append(
                    {
                        "id": name,
                        "value": name,
                        "label": name,
                        "name": name,
                    }
                )

    logger.warning(
        "payment_types: falling back to PaymentType enum (mode=%s, count=%d)",
        mode_normalized,
        len(items),
    )
    return items


@router.get("/patients")
def list_patients(
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> List[dict]:
    """
    Patients API for frontend autocomplete & tables.

    Normal path: read from DB (Patient model).
    Fallback path: when DB has no patients, read from CSV history in data/inputs/history.

    Output format:
        [{ "id": ..., "name": "...", "phone": "...", "payment_type": "..." }, ...]
    """
    from sqlalchemy import func

    total = db.query(func.count(Patient.id)).scalar() or 0

    if total > 0:
        # Normal path: DB-backed patients
        query = db.query(Patient)

        if search:
            term = f"%{search}%"
            query = query.filter(
                (Patient.name.ilike(term))
                | (Patient.phone.ilike(term))
                | (Patient.national_id.ilike(term))
            )

        patients = query.limit(limit).all()

        results: List[dict] = []
        for p in patients:
            results.append(
                {
                    "id": p.id,
                    "name": p.name,
                    "phone": p.phone,
                    "payment_type": getattr(p.payment_type, "value", None),
                }
            )
        return results

    # Fallback: DB empty – load from CSV history in data/inputs/history
    history_dir = "data/inputs/history"
    csv_path = None
    if os.path.isdir(history_dir):
        for filename in os.listdir(history_dir):
            if filename.lower().endswith(".csv"):
                csv_path = os.path.join(history_dir, filename)
                break

    if not csv_path or not os.path.exists(csv_path):
        return []

    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    # Try to resolve column names flexibly
    lower_map: Dict[str, str] = {c.lower(): c for c in df.columns}

    def pick(candidates: List[str]) -> Optional[str]:
        for cand in candidates:
            cand_l = cand.lower()
            if cand_l in lower_map:
                return lower_map[cand_l]
            # also allow "contains"
            for key, orig in lower_map.items():
                if cand_l in key:
                    return orig
        return None

    name_col = pick(["name", "full_name", "patient_name"])
    phone_col = pick(["phone", "mobile", "tel"])
    pay_col = pick(["payment_type", "payer_source", "insurance_type"])

    if not name_col or not phone_col:
        return []

    rows = df.dropna(subset=[name_col, phone_col])
    if search:
        rows = rows[rows[name_col].astype(str).str.contains(search, na=False)]

    results: List[dict] = []
    for idx, row in rows.head(limit).iterrows():
        results.append(
            {
                "id": int(idx),
                "name": str(row[name_col]),
                "phone": str(row[phone_col]),
                "payment_type": str(row[pay_col]) if pay_col and not pd.isna(row.get(pay_col)) else None,
            }
        )

    return results


@router.get("/appointments")
def list_appointments(future_only: bool = False) -> List[dict]:
    """
    Temporary stub endpoint for appointments.

    For now, always returns an empty list so that the frontend
    does not receive 404 for /appointments.
    """
    return []

