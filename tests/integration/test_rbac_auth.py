# -*- coding: utf-8 -*-
import pytest

from app.security.seed import ensure_seed_users
from models import User


def _login(client, username: str, password: str) -> str:
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def seeded_auth_users(test_db_session):
    ensure_seed_users(test_db_session)
    return {u.username: u for u in test_db_session.query(User).all()}


def test_owner_access_all(client, seeded_auth_users):
    token = _login(client, "nima_owner", "TEMP_CHANGE_ME_OWNER_123")
    h = _auth_headers(token)

    assert client.get("/api/manager/total-patients", headers=h).status_code == 200
    assert client.get("/api/import/ping", headers=h).status_code == 200
    assert client.get("/api/reception/search-patient?q=a", headers=h).status_code in (200, 503)


def test_clinic_manager_access_manager_blocked_owner_only(client, seeded_auth_users):
    token = _login(client, "clinic_manager", "TEMP_CHANGE_ME_MANAGER_123")
    h = _auth_headers(token)

    assert client.get("/api/manager/total-patients", headers=h).status_code == 200
    # Owner-only endpoint
    assert client.get("/api/admin/users", headers=h).status_code == 403


def test_operator_access_upload_blocked_manager(client, seeded_auth_users):
    token = _login(client, "clinic_operator", "TEMP_CHANGE_ME_OPERATOR_123")
    h = _auth_headers(token)

    assert client.get("/api/import/ping", headers=h).status_code == 200
    assert client.get("/api/manager/total-patients", headers=h).status_code == 403


def test_receptionist_access_reception_blocked_manager_and_operator(client, seeded_auth_users):
    token = _login(client, "reception1", "TEMP_CHANGE_ME_R1_123")
    h = _auth_headers(token)

    assert client.get("/api/reception/search-patient?q=a", headers=h).status_code in (200, 503)
    assert client.get("/api/manager/total-patients", headers=h).status_code == 403
    assert client.get("/api/import/ping", headers=h).status_code == 403


def test_self_service_change_password(client, seeded_auth_users):
    token = _login(client, "reception2", "TEMP_CHANGE_ME_R2_123")
    h = _auth_headers(token)

    res = client.post(
        "/api/auth/change-password",
        headers=h,
        json={"current_password": "TEMP_CHANGE_ME_R2_123", "new_password": "NewStrongPass_2026!"},
    )
    assert res.status_code == 200, res.text

    # Old password should fail, new password should work
    bad = client.post("/api/auth/login", json={"username": "reception2", "password": "TEMP_CHANGE_ME_R2_123"})
    assert bad.status_code == 401
    ok = client.post("/api/auth/login", json={"username": "reception2", "password": "NewStrongPass_2026!"})
    assert ok.status_code == 200, ok.text

