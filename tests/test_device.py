"""
tests/test_device.py
-----------------------
Pruebas unitarias para services/device_service.py y services/qr_service.py
"""

import pytest
from services import device_service, qr_service
from utils.error_handlers import ConflictError, NotFoundError


def test_connect_device_directly_success(fake_db):
    device = device_service.connect_device_directly("user-1", "iPhone 15", "phone")
    assert device["device_name"] == "iPhone 15"
    assert device["status"] == "connected"


def test_connect_device_duplicate_name_raises_conflict(fake_db):
    device_service.connect_device_directly("user-1", "iPhone 15", "phone")
    with pytest.raises(ConflictError):
        device_service.connect_device_directly("user-1", "iPhone 15", "phone")


def test_list_devices_only_returns_own_user_devices(fake_db):
    device_service.connect_device_directly("user-1", "iPhone 15", "phone")
    device_service.connect_device_directly("user-2", "Galaxy Watch", "watch")

    user1_devices = device_service.list_devices("user-1")
    assert len(user1_devices) == 1
    assert user1_devices[0]["device_name"] == "iPhone 15"


def test_disconnect_device_updates_status(fake_db):
    device = device_service.connect_device_directly("user-1", "iPhone 15", "phone")
    updated = device_service.disconnect_device("user-1", device["id"])
    assert updated["status"] == "disconnected"


def test_disconnect_device_not_owned_raises_not_found(fake_db):
    device = device_service.connect_device_directly("user-1", "iPhone 15", "phone")
    with pytest.raises(NotFoundError):
        device_service.disconnect_device("user-2", device["id"])


def test_generate_and_redeem_qr_success(fake_db):
    qr_data = qr_service.generate_device_qr("user-1", expiration_seconds=120)
    assert "qr_token" in qr_data
    assert qr_data["qr_image_base64"].startswith("data:image/png;base64,")

    device = qr_service.redeem_qr_token(
        qr_data["qr_token"], device_name="Huawei Watch GT", device_type="watch"
    )
    assert device["status"] == "connected"
    assert device["device_name"] == "Huawei Watch GT"


def test_redeem_invalid_qr_token_raises_not_found(fake_db):
    with pytest.raises(NotFoundError):
        qr_service.redeem_qr_token("invalid-token", "Reloj", "watch")


def test_redeem_qr_token_twice_fails(fake_db):
    qr_data = qr_service.generate_device_qr("user-1", expiration_seconds=120)
    qr_service.redeem_qr_token(qr_data["qr_token"], "Reloj 1", "watch")

    with pytest.raises(NotFoundError):
        qr_service.redeem_qr_token(qr_data["qr_token"], "Reloj 2", "watch")
