"""
services/qr_service.py
------------------------
Genera códigos QR temporales para vincular relojes inteligentes (u otros
wearables) a la cuenta de un usuario autenticado.

Flujo:
  1. El usuario autenticado solicita GET /device/qr.
  2. Se genera un token único (qr_token) y un código corto de 6 dígitos
     (pairing_code) equivalentes entre sí, y se crea un documento 'pending'
     en la colección 'devices' asociado a su user_id, con expiración.
  3. El QR (imagen PNG en base64) codifica el qr_token; el pairing_code se
     muestra además como texto para quien prefiera escribirlo a mano.
  4. El segundo dispositivo llama a POST /device/connect enviando el
     qr_token (si escaneó) o el pairing_code (si lo escribió), sin
     necesidad de sesión de navegador, lo que completa el vínculo y marca
     el dispositivo como 'connected'.
"""

import base64
import secrets
import io
from datetime import datetime, timedelta, timezone

import qrcode
from bson import ObjectId
from flask import session, current_app

from database.mongo import devices_collection
from models.device import build_pending_qr_device
from utils.error_handlers import NotFoundError, ConflictError
from utils.logger import log_activity


def generate_device_qr(user_id: str, expiration_seconds: int) -> dict:
    # Invalida cualquier QR pendiente previo del usuario para evitar tokens huérfanos
    devices_collection().delete_many({"user_id": user_id, "status": "pending"})

    qr_token = secrets.token_urlsafe(24)
    # Código corto alternativo al QR: pensado para escribirlo a mano cuando
    # escanear no es viable (sin cámara, red del hotspot, etc.), igual que
    # el código de sala de una trivia entre dos jugadores.
    pairing_code = f"{secrets.randbelow(1_000_000):06d}"
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expiration_seconds)

    pending_doc = build_pending_qr_device(user_id, qr_token, pairing_code, expires_at)
    devices_collection().insert_one(pending_doc)

    qr_image_base64 = _build_qr_image_base64(qr_token)

    log_activity(user_id, "device_qr_generated")

    return {
        "qr_token": qr_token,
        "pairing_code": pairing_code,
        "qr_image_base64": qr_image_base64,
        "expires_at": expires_at.isoformat(),
        "expires_in_seconds": expiration_seconds,
    }


def _build_qr_image_base64(qr_token: str) -> str:
    payload = f"healthmonitor://device-pair?token={qr_token}"
    img = qrcode.make(payload)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def redeem_qr_token(qr_token: str = None, pairing_code: str = None,
                     device_name: str = "", device_type: str = "watch") -> dict:
    """
    Llamado cuando un dispositivo (reloj) escanea el QR, o cuando la persona
    escribe a mano el código corto en vez de escanear. No requiere sesión de
    usuario: la identidad se deriva del token/código.
    """
    query = {"qr_token": qr_token, "status": "pending"} if qr_token \
        else {"pairing_code": pairing_code, "status": "pending"}
    pending_doc = devices_collection().find_one(query)

    if not pending_doc:
        raise NotFoundError("Código QR o código de vinculación inválido, o ya utilizado.")

    expires_at = pending_doc.get("expires_at")
    if expires_at and expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        devices_collection().delete_one({"_id": pending_doc["_id"]})
        raise ConflictError("El código QR ha expirado. Genera uno nuevo.")

    updated = devices_collection().find_one_and_update(
        {"_id": pending_doc["_id"]},
        {
            "$set": {
                "device_name": device_name.strip(),
                "device_type": device_type,
                "status": "connected",
                "connected_at": datetime.now(timezone.utc),
            },
            "$unset": {"qr_token": "", "expires_at": ""},
        },
        return_document=True,
    )

    log_activity(pending_doc["user_id"], "device_connected_via_qr", extra=device_name)

    # El dispositivo que escanea el QR queda autenticado como el mismo
    # usuario que lo generó (misma cuenta, sin necesidad de login manual),
    # ya que el qr_token por sí mismo demuestra la vinculación.
    session["user_id"] = pending_doc["user_id"]

    from models.device import serialize_device
    result = serialize_device(updated)

    # Avisa en tiempo real al dispositivo que generó el QR (ver useDeviceQr
    # en el frontend, que escucha "device_connected" para dejar de esperar).
    current_app.extensions["socketio"].emit(
        "device_connected", {"success": True, "data": result}, room=pending_doc["user_id"]
    )

    return result
