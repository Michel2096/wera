"""
services/simulator_service.py
--------------------------------
Genera datos biométricos simulados (no hay sensores reales) cada N
segundos para cada usuario conectado por WebSocket, los persiste en
MongoDB Atlas y los transmite en tiempo real a través de Flask-SocketIO.

Cada usuario solo recibe y almacena SUS PROPIOS datos: la emisión se
hace a una "room" de Socket.IO nombrada con el user_id, y los inserts en
Mongo siempre incluyen ese user_id, garantizando aislamiento entre
cuentas.
"""

import logging
import random
from datetime import datetime, timezone

from database.mongo import health_metrics_collection
from models.health_metric import build_health_metric_document, serialize_health_metric

logger = logging.getLogger("health_monitor.simulator")

# Usuarios actualmente conectados por WebSocket -> set de session ids (sid)
# usado para saber a quién seguir generando datos.
_connected_users = {}


def register_connection(user_id: str, sid: str):
    _connected_users.setdefault(user_id, set()).add(sid)
    logger.info("Usuario %s conectado (sid=%s). Total activos: %d",
                user_id, sid, len(_connected_users))


def unregister_connection(user_id: str, sid: str):
    if user_id in _connected_users:
        _connected_users[user_id].discard(sid)
        if not _connected_users[user_id]:
            del _connected_users[user_id]
    logger.info("Usuario %s desconectado (sid=%s).", user_id, sid)


def get_connected_user_ids():
    return list(_connected_users.keys())


def generate_random_metric(user_id: str) -> dict:
    """Genera una lectura biométrica simulada, con rangos fisiológicos
    plausibles inspirados en wearables reales (Huawei Health, etc)."""

    doc = build_health_metric_document(
        user_id=user_id,
        heart_rate=random.randint(55, 120),
        oxygen=round(random.uniform(94.0, 100.0), 1),
        steps=random.randint(0, 40),          # incremento por ciclo de 3s
        calories=round(random.uniform(0.1, 3.0), 2),
        distance=round(random.uniform(0.0, 0.03), 4),  # km por ciclo
        sleep=round(random.uniform(0, 9), 2),   # horas (snapshot diario simulado)
        stress=random.randint(1, 100),
        temperature=round(random.uniform(36.0, 37.8), 1),
    )

    result = health_metrics_collection().insert_one(doc)
    doc["_id"] = result.inserted_id

    return serialize_health_metric(doc)


def run_simulation_cycle(socketio):
    """Ejecuta un ciclo de generación para todos los usuarios conectados
    y emite el resultado únicamente a su room privada."""
    for user_id in get_connected_user_ids():
        try:
            metric = generate_random_metric(user_id)
            socketio.emit(
                "health_update",
                {"success": True, "data": metric},
                room=user_id,
            )
        except Exception as exc:
            logger.exception("Error generando métrica para %s: %s", user_id, exc)
