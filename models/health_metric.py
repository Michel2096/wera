"""
models/health_metric.py
------------------------
Colección: health_metrics
Campos: _id, user_id, heart_rate, oxygen, steps, calories, distance,
        sleep, stress, temperature, created_at
"""

from datetime import datetime, timezone


def build_health_metric_document(user_id, heart_rate, oxygen, steps,
                                  calories, distance, sleep, stress,
                                  temperature):
    return {
        "user_id": user_id,
        "heart_rate": heart_rate,
        "oxygen": oxygen,
        "steps": steps,
        "calories": calories,
        "distance": distance,
        "sleep": sleep,
        "stress": stress,
        "temperature": temperature,
        "created_at": datetime.now(timezone.utc),
    }


def serialize_health_metric(doc: dict) -> dict:
    if not doc:
        return None
    return {
        "id": str(doc["_id"]),
        "heart_rate": doc.get("heart_rate"),
        "oxygen": doc.get("oxygen"),
        "steps": doc.get("steps"),
        "calories": doc.get("calories"),
        "distance": doc.get("distance"),
        "sleep": doc.get("sleep"),
        "stress": doc.get("stress"),
        "temperature": doc.get("temperature"),
        "created_at": _iso(doc.get("created_at")),
    }


def _iso(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value
