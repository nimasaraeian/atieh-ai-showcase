# -*- coding: utf-8 -*-
"""
Insurance priority API – data from insurance_priority_rank table.
"""
import logging
import os
import sqlite3
from pathlib import Path

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/insurance", tags=["Insurance"])


def _get_db_path() -> str:
    db_url = os.getenv("DATABASE_URL", "sqlite:///atieh_clinic.db")
    if db_url.startswith("sqlite:///"):
        return db_url[len("sqlite:///"):]
    return db_url


@router.get("/priority")
def get_insurance_priority():
    """
    Return insurance priority ranks from insurance_priority_rank.

    Columns: insurance_name, payment_speed_group, priority_score
    """
    db_path = _get_db_path()
    if not Path(db_path).exists():
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='insurance_priority_rank'"
        )
        if not cur.fetchone():
            conn.close()
            return []

        rows = cur.execute(
            "SELECT insurance_name, payment_speed_group, priority_score FROM insurance_priority_rank ORDER BY priority_score DESC"
        ).fetchall()
        result = [
            {
                "insurance_name": r["insurance_name"],
                "payment_speed_group": r["payment_speed_group"],
                "priority_score": r["priority_score"],
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning("get_insurance_priority: %s", e)
        result = []
    finally:
        conn.close()

    return result
