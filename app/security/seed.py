# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy.orm import Session

from app.security.passwords import hash_password
from models import User, UserRole


SEED_USERS: list[dict] = [
    {"username": "nima_owner", "password": "TEMP_CHANGE_ME_OWNER_123", "role": UserRole.OWNER.value, "full_name": "Owner"},
    {"username": "clinic_manager", "password": "TEMP_CHANGE_ME_MANAGER_123", "role": UserRole.CLINIC_MANAGER.value, "full_name": "Clinic Manager"},
    {"username": "clinic_operator", "password": "TEMP_CHANGE_ME_OPERATOR_123", "role": UserRole.OPERATOR.value, "full_name": "Clinic Operator"},
    {"username": "reception1", "password": "TEMP_CHANGE_ME_R1_123", "role": UserRole.RECEPTIONIST.value, "full_name": "Receptionist 1"},
    {"username": "reception2", "password": "TEMP_CHANGE_ME_R2_123", "role": UserRole.RECEPTIONIST.value, "full_name": "Receptionist 2"},
    {"username": "reception3", "password": "TEMP_CHANGE_ME_R3_123", "role": UserRole.RECEPTIONIST.value, "full_name": "Receptionist 3"},
    {"username": "reception4", "password": "TEMP_CHANGE_ME_R4_123", "role": UserRole.RECEPTIONIST.value, "full_name": "Receptionist 4"},
    {"username": "reception5", "password": "TEMP_CHANGE_ME_R5_123", "role": UserRole.RECEPTIONIST.value, "full_name": "Receptionist 5"},
    {"username": "reception6", "password": "TEMP_CHANGE_ME_R6_123", "role": UserRole.RECEPTIONIST.value, "full_name": "Receptionist 6"},
    {"username": "reception7", "password": "TEMP_CHANGE_ME_R7_123", "role": UserRole.RECEPTIONIST.value, "full_name": "Receptionist 7"},
    {"username": "reception8", "password": "TEMP_CHANGE_ME_R8_123", "role": UserRole.RECEPTIONIST.value, "full_name": "Receptionist 8"},
    {"username": "reception9", "password": "TEMP_CHANGE_ME_R9_123", "role": UserRole.RECEPTIONIST.value, "full_name": "Receptionist 9"},
    {"username": "reception10", "password": "TEMP_CHANGE_ME_R10_123", "role": UserRole.RECEPTIONIST.value, "full_name": "Receptionist 10"},
]


def ensure_seed_users(db: Session) -> list[User]:
    """
    Idempotently create bootstrap users.
    - does NOT duplicate usernames
    - does NOT overwrite existing password hashes
    """
    now = datetime.now(timezone.utc)
    created: list[User] = []

    for u in SEED_USERS:
        username = u["username"]
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            continue
        user = User(
            username=username,
            password_hash=hash_password(u["password"]),
            full_name=u.get("full_name"),
            role=u["role"],
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(user)
        created.append(user)

    if created:
        db.commit()
        for u in created:
            db.refresh(u)

    return created

