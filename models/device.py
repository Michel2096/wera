"""
models/device.py
-----------------
Colección: devices
Campos: _id, user_id, device_name, device_type, status, qr_token, pairing_code, created_at

status: "pending" (QR generado, esperando escaneo) | "connected" | "disconnected"
device_type: "watch" | "phone" | "wearable"
"""

from datetime import datetime, timezone


def build_device_document(user_id, device_name, device_type,
                           status="connected", qr_token=None):
    return {
        "user_id": user_id,
        "device_name": device_name.strip(),
        "device_type": device_type,
        "status": status,
        "qr_token": qr_token,
        "created_at": datetime.now(timezone.utc),
    }


def build_pending_qr_device(user_id, qr_token, pairing_code, expires_at):
    return {
        "user_id": user_id,
        "device_name": None,
        "device_type": "watch",
        "status": "pending",
        "qr_token": qr_token,
        "pairing_code": pairing_code,
        "expires_at": expires_at,
        "created_at": datetime.now(timezone.utc),
    }


def serialize_device(device_doc: dict) -> dict:
    if not device_doc:
        return None
    return {
        "id": str(device_doc["_id"]),
        "device_name": device_doc.get("device_name"),
        "device_type": device_doc.get("device_type"),
        "status": device_doc.get("status"),
        "created_at": _iso(device_doc.get("created_at")),
        "connected_at": _iso(device_doc.get("connected_at")),
    }


def _iso(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value
