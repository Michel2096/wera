"""
models/user.py
---------------
Representación y serialización del documento 'users' en MongoDB.
Colección: users
Campos: _id, name, email, password_hash, birth_date, gender, weight,
        height, created_at
"""

from datetime import datetime, timezone


def build_user_document(name, email, password_hash, birth_date=None,
                         gender=None, weight=None, height=None):
    return {
        "name": name.strip(),
        "email": email.strip().lower(),
        "password_hash": password_hash,
        "birth_date": birth_date,
        "gender": gender,
        "weight": float(weight) if weight is not None else None,
        "height": float(height) if height is not None else None,
        "created_at": datetime.now(timezone.utc),
    }


def serialize_user(user_doc: dict) -> dict:
    """Convierte un documento de Mongo a un dict seguro para exponer al cliente
    (nunca incluye password_hash)."""
    if not user_doc:
        return None
    return {
        "id": str(user_doc["_id"]),
        "name": user_doc.get("name"),
        "email": user_doc.get("email"),
        "birth_date": user_doc.get("birth_date"),
        "gender": user_doc.get("gender"),
        "weight": user_doc.get("weight"),
        "height": user_doc.get("height"),
        "created_at": _iso(user_doc.get("created_at")),
    }


def _iso(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value
