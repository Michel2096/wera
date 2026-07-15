"""
models/activity_log.py
------------------------
Colección: activity_logs
Campos: _id, user_id, action, timestamp
"""

from datetime import datetime, timezone


def build_activity_log_document(user_id, action, extra=None):
    doc = {
        "user_id": user_id,
        "action": action,
        "timestamp": datetime.now(timezone.utc),
    }
    if extra:
        doc["extra"] = extra
    return doc


def serialize_activity_log(doc: dict) -> dict:
    if not doc:
        return None
    return {
        "id": str(doc["_id"]),
        "action": doc.get("action"),
        "timestamp": _iso(doc.get("timestamp")),
        "extra": doc.get("extra"),
    }


def _iso(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value
