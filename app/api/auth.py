# -*- coding: utf-8 -*-
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import User
from app.security.passwords import verify_password, hash_password
from app.security.jwt import create_access_token
from app.security.dependencies import get_current_user, AuthUser

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    username = payload.username.strip()
    u = db.query(User).filter(User.username == username).first()
    if not u or not verify_password(payload.password, u.password_hash):
        raise HTTPException(status_code=401, detail="invalid username or password")
    if not u.is_active:
        raise HTTPException(status_code=403, detail="user is inactive")
    role = u.role.value if getattr(u, "role", None) is not None else str(u.role or "")
    token = create_access_token(subject=u.username, user_id=u.id, role=role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name,
            "role": role,
            "is_active": bool(u.is_active),
        },
    }


@router.get("/me")
def me(user: AuthUser = Depends(get_current_user)):
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": bool(user.is_active),
    }


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == int(user.id)).first()
    if not u:
        raise HTTPException(status_code=404, detail="user not found")
    if not verify_password(payload.current_password, u.password_hash):
        raise HTTPException(status_code=401, detail="invalid current password")
    u.password_hash = hash_password(payload.new_password)
    db.add(u)
    db.commit()
    return {"ok": True}

