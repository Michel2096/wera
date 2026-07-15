"""
services/health_service.py
-----------------------------
Lógica de negocio para consultar métricas biométricas de un usuario:
lectura actual, historial paginado y estadísticas agregadas.

Cada registro biométrico está asociado estrictamente a un user_id,
garantizando que ningún usuario pueda ver datos de otra cuenta.
"""

from database.mongo import health_metrics_collection
from models.health_metric import serialize_health_metric
from utils.error_handlers import NotFoundError


def get_current_metric(user_id: str) -> dict:
    doc = health_metrics_collection().find_one(
        {"user_id": user_id}, sort=[("created_at", -1), ("_id", -1)]
    )
    if not doc:
        raise NotFoundError(
            "Aún no hay métricas biométricas registradas para este usuario. "
            "Conecta un dispositivo para iniciar la simulación."
        )
    return serialize_health_metric(doc)


def get_history(user_id: str, page: int = 1, limit: int = 50) -> dict:
    skip = (page - 1) * limit

    cursor = (
        health_metrics_collection()
        .find({"user_id": user_id})
        .sort([("created_at", -1), ("_id", -1)])
        .skip(skip)
        .limit(limit)
    )
    items = [serialize_health_metric(doc) for doc in cursor]

    total = health_metrics_collection().count_documents({"user_id": user_id})

    return {
        "items": items,
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": (total + limit - 1) // limit if limit else 0,
    }


def get_statistics(user_id: str) -> dict:
    # avg_/min_/max_ para cada métrica (consumidos por GET /health/statistics
    # en forma de {average, min, max} por métrica); total_* se conservan por
    # compatibilidad con el resumen agregado.
    pipeline = [
        {"$match": {"user_id": user_id}},
        {
            "$group": {
                "_id": None,
                "avg_heart_rate": {"$avg": "$heart_rate"},
                "min_heart_rate": {"$min": "$heart_rate"},
                "max_heart_rate": {"$max": "$heart_rate"},
                "avg_oxygen": {"$avg": "$oxygen"},
                "min_oxygen": {"$min": "$oxygen"},
                "max_oxygen": {"$max": "$oxygen"},
                "avg_steps": {"$avg": "$steps"},
                "min_steps": {"$min": "$steps"},
                "max_steps": {"$max": "$steps"},
                "avg_calories": {"$avg": "$calories"},
                "min_calories": {"$min": "$calories"},
                "max_calories": {"$max": "$calories"},
                "avg_distance": {"$avg": "$distance"},
                "min_distance": {"$min": "$distance"},
                "max_distance": {"$max": "$distance"},
                "avg_sleep": {"$avg": "$sleep"},
                "min_sleep": {"$min": "$sleep"},
                "max_sleep": {"$max": "$sleep"},
                "avg_stress": {"$avg": "$stress"},
                "min_stress": {"$min": "$stress"},
                "max_stress": {"$max": "$stress"},
                "avg_temperature": {"$avg": "$temperature"},
                "min_temperature": {"$min": "$temperature"},
                "max_temperature": {"$max": "$temperature"},
                "total_steps": {"$sum": "$steps"},
                "total_calories": {"$sum": "$calories"},
                "total_distance": {"$sum": "$distance"},
                "sample_count": {"$sum": 1},
            }
        },
    ]

    result = list(health_metrics_collection().aggregate(pipeline))

    if not result:
        zero_metrics = (
            "heart_rate", "oxygen", "steps", "calories", "distance", "sleep", "stress", "temperature",
        )
        stats = {"sample_count": 0, "total_steps": 0, "total_calories": 0, "total_distance": 0}
        for metric in zero_metrics:
            stats[f"avg_{metric}"] = None
            stats[f"min_{metric}"] = None
            stats[f"max_{metric}"] = None
        return stats

    stats = result[0]
    stats.pop("_id", None)

    # Redondeo para presentación
    for key, value in list(stats.items()):
        if key.startswith(("avg_", "min_", "max_")) and value is not None:
            stats[key] = round(value, 2)
    if stats.get("total_distance") is not None:
        stats["total_distance"] = round(stats["total_distance"], 2)

    return stats
