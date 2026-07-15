"""
services/auth_service.py
-------------------------
Lógica de negocio de autenticación mediante sesiones seguras de
servidor (sin JWT). Las contraseñas se protegen con bcrypt.
"""

import bcrypt
from flask import session
from database.mongo import users_collection
from models.user import build_user_document, serialize_user
from utils.error_handlers import ConflictError, AuthenticationError, NotFoundError
from utils.logger import log_activity


def _hash_password(plain_password: str, rounds: int = 12) -> str:
    salt = bcrypt.gensalt(rounds=rounds)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def _verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except ValueError:
        return False


def register_user(data: dict, bcrypt_rounds: int = 12) -> dict:
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
    )

    result = users_collection().insert_one(user_doc)
    user_doc["_id"] = result.inserted_id

    log_activity(str(result.inserted_id), "user_registered")

    return serialize_user(user_doc)


def login_user(data: dict) -> dict:
    email = data["email"].strip().lower()
    user_doc = users_collection().find_one({"email": email})

    if not user_doc or not _verify_password(data["password"], user_doc["password_hash"]):
        raise AuthenticationError("Correo o contraseña incorrectos.")

    # Sesión segura de servidor: solo guardamos el identificador del usuario.
    session.clear()
    session["user_id"] = str(user_doc["_id"])
    session["email"] = user_doc["email"]
    session.permanent = True

    log_activity(str(user_doc["_id"]), "user_login")

    return serialize_user(user_doc)


def logout_user():
    user_id = session.get("user_id")
    session.clear()
    if user_id:
        log_activity(user_id, "user_logout")


def get_current_session() -> dict:
    user_id = session.get("user_id")
    if not user_id:
        raise AuthenticationError("No hay una sesión activa.")

    from bson import ObjectId

    user_doc = users_collection().find_one({"_id": ObjectId(user_id)})
    if not user_doc:
        session.clear()
        raise NotFoundError("El usuario de la sesión ya no existe.")

    return {
        "authenticated": True,
        "user": serialize_user(user_doc),
    }
