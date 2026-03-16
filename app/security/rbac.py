# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Callable, Iterable

from fastapi import Depends, HTTPException

from app.security.dependencies import AuthUser, get_current_user


def require_roles(*allowed_roles: str) -> Callable:
    allowed = {str(r) for r in allowed_roles if r is not None}

    def _dep(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if user.role == "owner":
            return user
        if allowed and user.role in allowed:
            return user
        raise HTTPException(status_code=403, detail="forbidden")

    return _dep


def require_owner() -> Callable:
    return require_roles("owner")

