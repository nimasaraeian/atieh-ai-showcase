# -*- coding: utf-8 -*-

import logging
import sqlite3
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Body, HTTPException

from app.engine.db_schedule_recommender import recommend_slots_from_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ai/engine",
    tags=["AI Engine"],
)

DAY_MAP_FA_TO_EN = {
    "\u0634\u0646\u0628\u0647": "Saturday",
    "\u06cc\u06a9\u0634\u0646\u0628\u0647": "Sunday",
    "\u062f\u0648\u0634\u0646\u0628\u0647": "Monday",
    "\u0633\u0647 \u0634\u0646\u0628\u0647": "Tuesday",
    "\u0633\u0647\u200c\u0634\u0646\u0628\u0647": "Tuesday",
    "\u0686\u0647\u0627\u0631\u0634\u0646\u0628\u0647": "Wednesday",
    "\u067e\u0646\u062c\u0634\u0646\u0628\u0647": "Thursday",
    "\u062c\u0645\u0639\u0647": "Friday",
}

DB_PATH = "atieh_clinic.db"


@router.post("/recommend-slot")
def recommend_slot(payload: dict = Body(...)):
    try:
        preferred_day = payload.get("preferred_day")

        if not preferred_day and payload.get("weekday"):
            weekday_value = str(payload.get("weekday")).strip()
            preferred_day = DAY_MAP_FA_TO_EN.get(weekday_value, weekday_value)

        db_payload = {
            "record_no": payload.get("record_no"),
            "service": payload.get("service"),
            "insurance": payload.get("insurance"),
            "preferred_day": preferred_day,
        }

        logger.info("recommend-slot raw payload=%r", payload)
        logger.info("recommend-slot mapped preferred_day=%r", preferred_day)

        result = recommend_slots_from_db(db_payload, top_n=200)

        logger.info(
            "recommend-slot completed | count=%s | preferred_day_input=%s | preferred_day_mapped=%s",
            result.get("count"),
            result.get("preferred_day_input"),
            result.get("preferred_day_mapped"),
        )

        return result

    except Exception as e:
        logger.exception("Scheduling engine failed")
        raise HTTPException(
            status_code=500,
            detail=f"Scheduling engine error: {e}",
        ) from e


def _resolve_catalog_path(candidates):
    for p in candidates:
        path = Path(p)
        if path.exists():
            return str(path)
    return None


@router.get("/catalog/services")
def get_services():
    path = _resolve_catalog_path([
        "data/reference/services_catalog.csv",
        "data/outputs/services_catalog.csv",
        "data/inputs/reference/services_catalog.csv",
    ])

    if not path:
        logger.warning("services catalog not found; returning empty list")
        return []

    df = pd.read_csv(path, encoding="utf-8-sig")
    col = "service_name" if "service_name" in df.columns else df.columns[0]

    return df[col].dropna().astype(str).unique().tolist()


@router.get("/catalog/insurances")
def get_insurances():
    """
    Return insurance catalog for dropdowns in the AI scheduling form.

    Priority:
      1) Normalized DB tables/views (stg_payments, insurance_priority / v_insurance_priority)
      2) CSV catalogs in data/...
    """
    # 1) Try to load from SQLite DB (normalized sources)
    items: list[dict] = []
    try:
      conn = sqlite3.connect(DB_PATH)
      conn.row_factory = sqlite3.Row
      cur = conn.cursor()

      # 1a) stg_payments: distinct insurer_name_norm
      exists = cur.execute(
          "SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name = 'stg_payments'"
      ).fetchone()
      if exists:
          rows = cur.execute(
              "SELECT DISTINCT insurer_name_norm "
              "FROM stg_payments WHERE insurer_name_norm IS NOT NULL"
          ).fetchall()
          for (name,) in rows:
              n = str(name)
              if not n:
                  continue
              items.append(
                  {
                      "id": n,
                      "value": n,
                      "label": n,
                      "name": n,
                  }
              )

      # 1b) Fallback to insurance_priority / v_insurance_priority
      if not items:
          for table in ["insurance_priority", "v_insurance_priority"]:
              exists = cur.execute(
                  "SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name = ?",
                  (table,),
              ).fetchone()
              if not exists:
                  continue

              cols = [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]
              name_col = None
              for cand in ["insurer_name_norm", "insurance_name"]:
                  if cand in cols:
                      name_col = cand
                      break
              score_col = "priority_score" if "priority_score" in cols else None
              if not name_col:
                  continue

              select_cols = [name_col]
              if score_col:
                  select_cols.append(score_col)
              rows = cur.execute(
                  f"SELECT {', '.join(select_cols)} FROM {table} "
                  f"WHERE {name_col} IS NOT NULL"
              ).fetchall()

              for row in rows:
                  n = str(row[name_col])
                  if not n:
                      continue
                  item = {
                      "id": n,
                      "value": n,
                      "label": n,
                      "name": n,
                  }
                  if score_col:
                      try:
                          score_val = row[score_col]
                          if score_val is not None:
                              item["priority_score"] = float(score_val)
                      except (TypeError, ValueError):
                          pass
                  items.append(item)

      conn.close()
    except Exception as exc:
        logger.warning("get_insurances: DB lookup failed – %s", exc)

    if items:
        # Sort by priority_score (descending) when available, otherwise by name.
        items.sort(
            key=lambda x: (
                -float(x.get("priority_score", 0.0)),
                str(x.get("label") or x.get("name") or ""),
            )
        )
        return items

    # 2) Fall back to CSV catalogs
    path = _resolve_catalog_path([
        "data/reference/insurance_payment_priority.csv",
        "data/outputs/insurance_priority.csv",
        "data/inputs/payments/insurance_payment_priority.csv",
        "data/reference/insurance_priority.csv",
    ])

    if not path:
        logger.warning("insurance catalog not found; returning empty list")
        return []

    df = pd.read_csv(path, encoding="utf-8-sig")

    # Pick a reasonable display/name column
    col = next(
        (
            c
            for c in [
                "insurance_name",
                "insurer_name_norm",
                "payer_source_norm",
            ]
            if c in df.columns
        ),
        df.columns[0],
    )

    score_col = "priority_score" if "priority_score" in df.columns else None

    df = df.dropna(subset=[col]).drop_duplicates(subset=[col])

    items = []
    for _, row in df.iterrows():
        name = str(row[col])
        item = {
            "id": name,
            "value": name,
            "label": name,
            "name": name,
        }
        if score_col is not None:
            try:
                score_val = row.get(score_col)
                if score_val is not None:
                    item["priority_score"] = float(score_val)
            except (TypeError, ValueError):
                # Ignore non-numeric scores; frontend and engine will fall back to defaults.
                pass
        items.append(item)

    # Sort by priority_score (descending) when available, otherwise by name.
    items.sort(
        key=lambda x: (
            -float(x.get("priority_score", 0.0)),
            str(x.get("label") or x.get("name") or ""),
        )
    )

    return items