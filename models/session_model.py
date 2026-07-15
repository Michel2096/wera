"""
models/session_model.py
------------------------
Colección: sessions
Campos: _id, user_id, session_id, created_at

Nota: el ciclo de vida completo de este documento (creación, expiración
TTL, serialización binaria) es administrado por Flask-Session mediante
su backend de MongoDB. Este módulo expone helpers de solo lectura útiles
para el endpoint GET /auth/session y para auditoría.
"""

from datetime import datetime, timezone


def serialize_session(session_doc: dict) -> dict:
    if not session_doc:
        return None
    return {
        "session_id": session_doc.get("session_id") or session_doc.get("id"),
        "user_id": session_doc.get("user_id"),
        "created_at": _iso(session_doc.get("created_at") or session_doc.get("creation")),
    }


def _iso(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value
