import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


def _bool_env(key: str, default: bool = False) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


class Config:
    """Configuración base compartida por todos los entornos."""

    # --- Flask core ---
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-not-for-production")
    DEBUG = _bool_env("FLASK_DEBUG", False)
    ENV = os.getenv("FLASK_ENV", "production")

    # --- Servidor / Red local ---
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 5000))

    # --- MongoDB Atlas ---
    MONGO_URI = os.getenv("MONGO_URI")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "health_monitor_db")

    # --- Flask-Session (persistida en MongoDB Atlas) ---
    SESSION_TYPE = "mongodb"  # manejado manualmente vía database/mongo.py
    SESSION_MONGO_COLLECTION = os.getenv("SESSION_MONGO_COLLECTION", "sessions")
    SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "health_monitor_session")
    SESSION_PERMANENT = _bool_env("SESSION_PERMANENT", False)
    SESSION_USE_SIGNER = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = _bool_env("SESSION_COOKIE_SECURE", False)
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    PERMANENT_SESSION_LIFETIME = timedelta(
        hours=int(os.getenv("SESSION_LIFETIME_HOURS", 12))
    )

    # --- CORS ---
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

    # --- Simulador biométrico ---
    SIMULATION_INTERVAL_SECONDS = int(os.getenv("SIMULATION_INTERVAL_SECONDS", 3))

    # --- QR de vinculación ---
    QR_TOKEN_EXPIRATION_SECONDS = int(os.getenv("QR_TOKEN_EXPIRATION_SECONDS", 120))

    # --- Seguridad de contraseñas ---
    BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", 12))

    # --- Logging ---
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")

    # --- Swagger / OpenAPI ---
    SWAGGER = {
        "title": "Health Monitor API",
        "uiversion": 3,
        "specs_route": "/docs/",
        "version": "1.0.0",
        "description": (
            "API REST de monitoreo de salud (inspirada en Huawei Health). "
            "Autenticación por sesiones seguras, métricas biométricas simuladas, "
            "sincronización en tiempo real vía WebSockets y vinculación de "
            "dispositivos por código QR."
        ),
    }


class DevelopmentConfig(Config):
    DEBUG = True
    ENV = "development"


class ProductionConfig(Config):
    DEBUG = False
    ENV = "production"
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    DEBUG = True
    ENV = "testing"
    MONGO_DB_NAME = "health_monitor_test_db"


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config():
    env = os.getenv("FLASK_ENV", "development")
    return config_by_name.get(env, DevelopmentConfig)
