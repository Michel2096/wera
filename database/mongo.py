"""
database/mongo.py
------------------
Punto único de conexión a MongoDB Atlas mediante PyMongo.
Expone un objeto `db` inicializado en tiempo de arranque de la app
(patrón singleton simple) y helpers para obtener cada colección.
"""

import logging
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, ConfigurationError

logger = logging.getLogger("health_monitor.database")

_client: MongoClient | None = None
_db = None


def init_db(app):
    """
    Inicializa la conexión a MongoDB Atlas usando la configuración de la app
    y crea los índices necesarios. Debe llamarse una sola vez, en app.py.
    """
    global _client, _db

    mongo_uri = app.config.get("MONGO_URI")
    db_name = app.config.get("MONGO_DB_NAME")

    if not mongo_uri:
        raise RuntimeError(
            "MONGO_URI no está configurado. Define esta variable en tu archivo .env "
            "con la cadena de conexión de tu clúster de MongoDB Atlas."
        )

    try:
        _client = MongoClient(mongo_uri, serverSelectionTimeoutMS=8000)
        # Fuerza la validación de la conexión al arrancar
        _client.admin.command("ping")
        _db = _client[db_name]
        logger.info("Conexión exitosa a MongoDB Atlas (base de datos: %s)", db_name)
    except (ConnectionFailure, ConfigurationError) as exc:
        logger.error("Error conectando a MongoDB Atlas: %s", exc)
        raise

    _create_indexes()
    return _db


def _create_indexes():
    """Crea índices para garantizar integridad y rendimiento de consultas."""
    if _db is None:
        return

    # users: email único
    _db.users.create_index([("email", ASCENDING)], unique=True)

    # devices: por usuario y por qr_token
    _db.devices.create_index([("user_id", ASCENDING)])
    _db.devices.create_index([("qr_token", ASCENDING)])

    # health_metrics: por usuario + fecha, para consultas de historial rápidas
    _db.health_metrics.create_index(
        [("user_id", ASCENDING), ("created_at", DESCENDING)]
    )

    # sessions: el índice único ("id") y el TTL ("expiration") los crea
    # Flask-Session al inicializarse (ver flask_session/mongodb/mongodb.py).
    # No declarar índices propios aquí: los campos "session_id"/"expires_at"
    # no existen en los documentos que genera esa librería.

    # activity_logs: por usuario + fecha
    _db.activity_logs.create_index(
        [("user_id", ASCENDING), ("timestamp", DESCENDING)]
    )

    logger.info("Índices de MongoDB verificados/creados correctamente.")


def get_db():
    """Devuelve la instancia activa de la base de datos."""
    if _db is None:
        raise RuntimeError(
            "La base de datos no ha sido inicializada. Llama a init_db(app) primero."
        )
    return _db


# --- Helpers de acceso directo a colecciones ---

def users_collection():
    return get_db().users


def devices_collection():
    return get_db().devices


def health_metrics_collection():
    return get_db().health_metrics


def sessions_collection():
    return get_db().sessions


def activity_logs_collection():
    return get_db().activity_logs
