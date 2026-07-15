"""
tests/test_auth.py
---------------------
Pruebas unitarias para services/auth_service.py
"""

import pytest
from services import auth_service
from utils.error_handlers import ConflictError, AuthenticationError


VALID_USER = {
    "name": "Taurus López",
    "email": "taurus@example.com",
    "password": "SuperSecret123",
    "birth_date": "2000-05-14",
    "gender": "male",
    "weight": 70,
    "height": 175,
}


def test_register_user_success(fake_db):
    user = auth_service.register_user(VALID_USER)
    assert user["email"] == "taurus@example.com"
    assert "password_hash" not in user
    assert fake_db.users.count_documents({}) == 1


def test_register_user_duplicate_email_raises_conflict(fake_db):
    auth_service.register_user(VALID_USER)
    with pytest.raises(ConflictError):
        auth_service.register_user(VALID_USER)


def test_login_user_success(fake_db, flask_session):
    auth_service.register_user(VALID_USER)
    result = auth_service.login_user(
        {"email": VALID_USER["email"], "password": VALID_USER["password"]}
    )
    assert result["email"] == VALID_USER["email"]
    assert flask_session.get("user_id") is not None


def test_login_user_wrong_password_raises_authentication_error(fake_db, flask_session):
    auth_service.register_user(VALID_USER)
    with pytest.raises(AuthenticationError):
        auth_service.login_user(
            {"email": VALID_USER["email"], "password": "wrong-password"}
        )


def test_login_user_unknown_email_raises_authentication_error(fake_db, flask_session):
    with pytest.raises(AuthenticationError):
        auth_service.login_user(
            {"email": "unknown@example.com", "password": "whatever123"}
        )


def test_logout_clears_session(fake_db, flask_session):
    auth_service.register_user(VALID_USER)
    auth_service.login_user(
        {"email": VALID_USER["email"], "password": VALID_USER["password"]}
    )
    auth_service.logout_user()
    assert "user_id" not in flask_session
