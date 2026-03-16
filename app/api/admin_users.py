# -*- coding: utf-8 -*-
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import User
from app.security.passwords import hash_password
from app.security.rbac import require_owner

router = APIRouter(prefix="/api/admin/users", tags=["admin"], dependencies=[Depends(require_owner())])


@router.get("")
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.id.asc()).all()
    out = []
    for u in users:
        out.append(
            {
                "id": u.id,
                "username": u.username,
                "full_name": u.full_name,
                "role": u.role.value if getattr(u, "role", None) is not None else u.role,
                "is_active": bool(u.is_active),
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "updated_at": u.updated_at.isoformat() if u.updated_at else None,
            }
        )
    return {"data": out}


class SetActiveRequest(BaseModel):
    is_active: bool


@router.post("/{user_id}/active")
def set_active(user_id: int, payload: SetActiveRequest, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="user not found")
    u.is_active = bool(payload.is_active)
    db.add(u)
    db.commit()
    db.refresh(u)
    return {"ok": True, "id": u.id, "is_active": bool(u.is_active)}


class ResetPasswordRequest(BaseModel):
    password: str = Field(..., min_length=8)


@router.post("/{user_id}/reset-password")
def reset_password(user_id: int, payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="user not found")
    u.password_hash = hash_password(payload.password)
    db.add(u)
    db.commit()
    return {"ok": True, "id": u.id}

