# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt


def _secret_key() -> str:
    # Prefer explicit production secret.
    key = (os.getenv("ATIEH_AUTH_SECRET") or os.getenv("SECRET_KEY") or "").strip()
    if key:
        return key
    # Safe fallback for local/dev/tests (deployment note will require overriding).
    return "DEV_ONLY_INSECURE_CHANGE_ME"


ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("ATIEH_AUTH_TOKEN_EXPIRE_HOURS", "12"))


def create_access_token(*, subject: str, user_id: int, role: str, expires_delta: Optional[timedelta] = None) -> str:
    now = datetime.now(timezone.utc)
    exp = now + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    payload: dict[str, Any] = {
        "sub": subject,
        "uid": int(user_id),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": exp,
    }
    return jwt.encode(payload, _secret_key(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, _secret_key(), algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("invalid token") from exc

