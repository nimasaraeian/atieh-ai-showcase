# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from models import User
from app.security.jwt import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


@dataclass(frozen=True)
class AuthUser:
    id: int
    username: str
    full_name: Optional[str]
    role: str
    is_active: bool


def _auth_disabled() -> bool:
    return (os.getenv("AUTH_DISABLED") or "").strip() == "1"


def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Optional[AuthUser]:
    if not token:
        return None
    try:
        payload = decode_access_token(token)
    except Exception:
        return None
    user_id = payload.get("uid")
    if not user_id:
        return None
    u = db.query(User).filter(User.id == int(user_id)).first()
    if not u:
        return None
    return AuthUser(
        id=u.id,
        username=u.username,
        full_name=u.full_name,
        role=(u.role.value if getattr(u, "role", None) is not None else str(payload.get("role") or "")),
        is_active=bool(u.is_active),
    )


def get_current_user(
    user: Optional[AuthUser] = Depends(get_current_user_optional),
) -> AuthUser:
    if user is None:
        if _auth_disabled():
            # In legacy/dev mode, treat requests as unauthenticated but allowed
            # only on endpoints that opt-in to allowing anonymous access.
            raise HTTPException(status_code=401, detail="authentication disabled: no user")
        raise HTTPException(status_code=401, detail="not authenticated")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="user is inactive")
    return user

