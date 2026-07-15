import re
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from bson.errors import InvalidId
from flask import session

from database.mongo import (
    users_collection,
    devices_collection,
    health_metrics_collection,
    activity_logs_collection,
)
from models.user import build_user_document, serialize_user
from models.activity_log import serialize_activity_log
from services.auth_service import _hash_password, _verify_password
from utils.error_handlers import NotFoundError, ConflictError, AuthenticationError, AuthorizationError
from utils.logger import log_activity


def _to_object_id(user_id: str) -> ObjectId:
    try:
        return ObjectId(user_id)
    except (InvalidId, TypeError):
        raise NotFoundError("Identificador de usuario inválido.")


def _admin_count(exclude_user_id: str = None) -> int:
    query = {"role": "admin"}
    if exclude_user_id:
        query["_id"] = {"$ne": _to_object_id(exclude_user_id)}
    return users_collection().count_documents(query)


# --- Autenticación de administrador ---

def login_admin(data: dict) -> dict:
    """
    Login exclusivo para administradores. Verifica credenciales igual que
    el login público, pero además exige role='admin': un usuario regular
    con contraseña correcta recibe 403, no una sesión.
    """
    email = data["email"].strip().lower()
    user_doc = users_collection().find_one({"email": email})

    if not user_doc or not _verify_password(data["password"], user_doc["password_hash"]):
        raise AuthenticationError("Correo o contraseña incorrectos.")

    if user_doc.get("role") != "admin":
        raise AuthorizationError("Esta cuenta no tiene privilegios de administrador.")

    if not user_doc.get("is_active", True):
        raise AuthenticationError("Esta cuenta ha sido deshabilitada. Contacta a otro administrador.")

    session.clear()
    session["user_id"] = str(user_doc["_id"])
    session["email"] = user_doc["email"]
    session["role"] = user_doc["role"]
    session.permanent = True

    log_activity(str(user_doc["_id"]), "admin_login")

    return serialize_user(user_doc)


def logout_admin() -> None:
    user_id = session.get("user_id")
    session.clear()
    if user_id:
        log_activity(user_id, "admin_logout")


def register_admin(data: dict, bcrypt_rounds: int = 12, actor_id: str = None) -> dict:
    """
    Registra una nueva cuenta con role='admin'. A diferencia de
    auth_service.register_user (registro público, siempre role='user'),
    esta función fuerza role='admin' sin importar lo que envíe el
    llamador, y solo debe exponerse detrás de una ruta protegida con
    @admin_required (un admin registra a otro).
    """
    payload = dict(data)
    payload["role"] = "admin"
    payload.setdefault("is_active", True)
    return create_user(payload, bcrypt_rounds, actor_id=actor_id)


# --- CRUD de usuarios ---

def list_users(page: int = 1, limit: int = 50, search: str = None,
                role: str = None, is_active: bool = None) -> dict:
    query = {}

    if search:
        escaped = re.escape(search.strip())
        query["$or"] = [
            {"name": {"$regex": escaped, "$options": "i"}},
            {"email": {"$regex": escaped, "$options": "i"}},
        ]

    if role in ("user", "admin"):
        query["role"] = role

    if is_active is not None:
        query["is_active"] = is_active

    skip = (page - 1) * limit

    cursor = (
        users_collection()
        .find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    items = [serialize_user(doc) for doc in cursor]
    total = users_collection().count_documents(query)

    return {
        "items": items,
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": (total + limit - 1) // limit if limit else 0,
    }


def get_user(user_id: str) -> dict:
    doc = users_collection().find_one({"_id": _to_object_id(user_id)})
    if not doc:
        raise NotFoundError("Usuario no encontrado.")
    return serialize_user(doc)


def create_user(data: dict, bcrypt_rounds: int = 12, actor_id: str = None) -> dict:
    email = data["email"].strip().lower()

    if users_collection().find_one({"email": email}):
        raise ConflictError("Ya existe una cuenta registrada con este correo.")

    password_hash = _hash_password(data["password"], bcrypt_rounds)

    user_doc = build_user_document(
        name=data["name"],
        email=email,
        password_hash=password_hash,
        birth_date=data.get("birth_date"),
        gender=data.get("gender"),
        weight=data.get("weight"),
        height=data.get("height"),
        role=data.get("role", "user"),
        is_active=data.get("is_active", True),
    )

    result = users_collection().insert_one(user_doc)
    user_doc["_id"] = result.inserted_id

    log_activity(actor_id, "admin_user_created", extra=str(result.inserted_id))

    return serialize_user(user_doc)


def update_user(user_id: str, data: dict, bcrypt_rounds: int = 12, actor_id: str = None) -> dict:
    object_id = _to_object_id(user_id)
    existing = users_collection().find_one({"_id": object_id})
    if not existing:
        raise NotFoundError("Usuario no encontrado.")

    update_fields = {}

    if "name" in data and data["name"]:
        update_fields["name"] = data["name"].strip()

    if "email" in data and data["email"]:
        new_email = data["email"].strip().lower()
        if new_email != existing["email"] and users_collection().find_one({"email": new_email}):
            raise ConflictError("Ya existe una cuenta registrada con este correo.")
        update_fields["email"] = new_email

    if "password" in data and data["password"]:
        update_fields["password_hash"] = _hash_password(data["password"], bcrypt_rounds)

    for field in ("birth_date", "gender"):
        if field in data:
            update_fields[field] = data[field]

    for numeric_field in ("weight", "height"):
        if numeric_field in data and data[numeric_field] is not None:
            update_fields[numeric_field] = float(data[numeric_field])

    if "role" in data:
        # Evita quedarse sin ningún administrador en la plataforma.
        if existing.get("role") == "admin" and data["role"] != "admin" and _admin_count(exclude_user_id=user_id) == 0:
            raise ConflictError("No puedes quitar el rol de administrador al último administrador existente.")
        update_fields["role"] = data["role"]

    if "is_active" in data:
        if existing.get("role") == "admin" and data["is_active"] is False and _admin_count(exclude_user_id=user_id) == 0:
            raise ConflictError("No puedes deshabilitar al último administrador existente.")
        update_fields["is_active"] = data["is_active"]

    if not update_fields:
        return serialize_user(existing)

    updated = users_collection().find_one_and_update(
        {"_id": object_id},
        {"$set": update_fields},
        return_document=True,
    )

    log_activity(actor_id, "admin_user_updated", extra={"target": user_id, "fields": list(update_fields.keys())})

    return serialize_user(updated)


def update_user_role(user_id: str, role: str, actor_id: str = None) -> dict:
    return update_user(user_id, {"role": role}, actor_id=actor_id)


def delete_user(user_id: str, actor_id: str = None) -> None:
    object_id = _to_object_id(user_id)
    existing = users_collection().find_one({"_id": object_id})
    if not existing:
        raise NotFoundError("Usuario no encontrado.")

    if existing.get("role") == "admin" and _admin_count(exclude_user_id=user_id) == 0:
        raise ConflictError("No puedes eliminar al último administrador existente.")

    users_collection().delete_one({"_id": object_id})

    # Limpieza en cascada de los datos asociados al usuario eliminado.
    devices_collection().delete_many({"user_id": user_id})
    health_metrics_collection().delete_many({"user_id": user_id})
    activity_logs_collection().delete_many({"user_id": user_id})

    log_activity(actor_id, "admin_user_deleted", extra=user_id)


# --- Estadísticas globales de la plataforma ---

def get_platform_statistics() -> dict:
    now = datetime.now(timezone.utc)
    last_7_days = now - timedelta(days=7)
    last_30_days = now - timedelta(days=30)

    total_users = users_collection().count_documents({})
    total_admins = users_collection().count_documents({"role": "admin"})
    active_users = users_collection().count_documents({"is_active": True})
    inactive_users = total_users - active_users

    new_users_7d = users_collection().count_documents({"created_at": {"$gte": last_7_days}})
    new_users_30d = users_collection().count_documents({"created_at": {"$gte": last_30_days}})

    gender_pipeline = [{"$group": {"_id": "$gender", "count": {"$sum": 1}}}]
    users_by_gender = {
        (doc["_id"] or "unknown"): doc["count"]
        for doc in users_collection().aggregate(gender_pipeline)
    }

    total_devices = devices_collection().count_documents({})
    devices_by_status_pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    devices_by_status = {
        (doc["_id"] or "unknown"): doc["count"]
        for doc in devices_collection().aggregate(devices_by_status_pipeline)
    }
    devices_by_type_pipeline = [{"$group": {"_id": "$device_type", "count": {"$sum": 1}}}]
    devices_by_type = {
        (doc["_id"] or "unknown"): doc["count"]
        for doc in devices_collection().aggregate(devices_by_type_pipeline)
    }

    total_health_metrics = health_metrics_collection().count_documents({})

    platform_avg_pipeline = [
        {
            "$group": {
                "_id": None,
                "avg_heart_rate": {"$avg": "$heart_rate"},
                "avg_oxygen": {"$avg": "$oxygen"},
                "avg_steps": {"$avg": "$steps"},
                "avg_calories": {"$avg": "$calories"},
                "avg_sleep": {"$avg": "$sleep"},
                "avg_stress": {"$avg": "$stress"},
            }
        }
    ]
    platform_avg_result = list(health_metrics_collection().aggregate(platform_avg_pipeline))
    platform_averages = platform_avg_result[0] if platform_avg_result else {}
    platform_averages.pop("_id", None)
    for key, value in list(platform_averages.items()):
        if value is not None:
            platform_averages[key] = round(value, 2)

    total_activity_logs = activity_logs_collection().count_documents({})

    return {
        "users": {
            "total": total_users,
            "admins": total_admins,
            "regular": total_users - total_admins,
            "active": active_users,
            "inactive": inactive_users,
            "new_last_7_days": new_users_7d,
            "new_last_30_days": new_users_30d,
            "by_gender": users_by_gender,
        },
        "devices": {
            "total": total_devices,
            "by_status": devices_by_status,
            "by_type": devices_by_type,
        },
        "health_metrics": {
            "total_samples": total_health_metrics,
            "platform_averages": platform_averages,
        },
        "activity_logs": {
            "total": total_activity_logs,
        },
    }


def get_user_growth(days: int = 30) -> list:
    """Devuelve el número de usuarios nuevos registrados por día en los
    últimos `days` días, útil para graficar tendencias en el panel admin."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)

    pipeline = [
        {"$match": {"created_at": {"$gte": start}}},
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ]

    results = list(users_collection().aggregate(pipeline))
    return [{"date": doc["_id"], "new_users": doc["count"]} for doc in results]


# --- Auditoría ---

def list_activity_logs(page: int = 1, limit: int = 50, user_id: str = None, action: str = None) -> dict:
    query = {}
    if user_id:
        query["user_id"] = user_id
    if action:
        query["action"] = action

    skip = (page - 1) * limit

    cursor = (
        activity_logs_collection()
        .find(query)
        .sort("timestamp", -1)
        .skip(skip)
        .limit(limit)
    )
    items = [serialize_activity_log(doc) for doc in cursor]
    total = activity_logs_collection().count_documents(query)

    return {
        "items": items,
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": (total + limit - 1) // limit if limit else 0,
    }
