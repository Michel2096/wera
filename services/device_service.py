"""
services/device_service.py
-----------------------------
Lógica de negocio para conectar, listar y desconectar dispositivos
(teléfonos, relojes inteligentes y futuros wearables) asociados a un
usuario. Un usuario puede tener múltiples dispositivos conectados.
"""

from datetime import datetime, timezone
from bson import ObjectId

from database.mongo import devices_collection
from models.device import build_device_document, serialize_device
from utils.error_handlers import NotFoundError, ConflictError
from utils.logger import log_activity


def connect_device_directly(user_id: str, device_name: str, device_type: str) -> dict:
    """
    Conexión directa de un dispositivo sin flujo QR (por ejemplo, la app
    móvil del propio usuario, ya autenticado por sesión, registrándose
    a sí misma como dispositivo 'phone').
    """
    existing = devices_collection().find_one(
        {
            "user_id": user_id,
            "device_name": device_name.strip(),
            "status": "connected",
        }
    )
    if existing:
        raise ConflictError("Ya existe un dispositivo conectado con ese nombre.")

    device_doc = build_device_document(
        user_id=user_id,
        device_name=device_name,
        device_type=device_type,
        status="connected",
    )
    device_doc["connected_at"] = datetime.now(timezone.utc)

    result = devices_collection().insert_one(device_doc)
    device_doc["_id"] = result.inserted_id

    log_activity(user_id, "device_connected", extra=device_name)

    return serialize_device(device_doc)


def list_devices(user_id: str) -> list:
    docs = devices_collection().find(
        {"user_id": user_id, "status": {"$ne": "pending"}}
    ).sort("created_at", -1)
    return [serialize_device(doc) for doc in docs]


def disconnect_device(user_id: str, device_id: str) -> dict:
    try:
        object_id = ObjectId(device_id)
    except Exception:
        raise NotFoundError("Identificador de dispositivo inválido.")

    device_doc = devices_collection().find_one({"_id": object_id, "user_id": user_id})
    if not device_doc:
        raise NotFoundError("Dispositivo no encontrado para este usuario.")

    updated = devices_collection().find_one_and_update(
        {"_id": object_id},
        {"$set": {"status": "disconnected", "disconnected_at": datetime.now(timezone.utc)}},
        return_document=True,
    )

    log_activity(user_id, "device_disconnected", extra=device_doc.get("device_name"))

    return serialize_device(updated)
