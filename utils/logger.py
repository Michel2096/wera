"""
utils/logger.py
----------------
Configura logging de aplicación (consola + archivo rotativo) y expone
un helper para registrar actividad de usuario en la colección
`activity_logs` de MongoDB (auditoría / trazabilidad).
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone


def setup_logging(app):
    log_level = app.config.get("LOG_LEVEL", "INFO")
    log_file = app.config.get("LOG_FILE", "logs/app.log")

    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    root_logger = logging.getLogger("health_monitor")
    root_logger.setLevel(log_level)

    if not root_logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        file_handler = RotatingFileHandler(
            log_file, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    return root_logger


def log_activity(user_id, action, extra=None):
    """
    Inserta un registro de auditoría en la colección activity_logs.
    Se usa en servicios sensibles (login, registro de dispositivo, etc).
    """
    from database.mongo import activity_logs_collection

    entry = {
        "user_id": user_id,
        "action": action,
        "timestamp": datetime.now(timezone.utc),
    }
    if extra:
        entry["extra"] = extra

    try:
        activity_logs_collection().insert_one(entry)
    except Exception as exc:  # nunca debe romper el flujo principal
        logging.getLogger("health_monitor.activity").warning(
            "No se pudo registrar actividad: %s", exc
        )
