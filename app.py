import logging

import eventlet
eventlet.monkey_patch()

from flask import Flask, redirect
from flask_cors import CORS
from flask_session import Session
from flask_socketio import SocketIO
from flasgger import Swagger
from pymongo import MongoClient

from config import get_config
from database.mongo import init_db
from utils.logger import setup_logging
from utils.error_handlers import register_error_handlers

from routes.auth_routes import auth_bp
from routes.profile_routes import profile_bp
from routes.health_routes import health_bp
from routes.device_routes import device_bp
from routes.dashboard_routes import dashboard_bp

from sockets.health_socket import register_socket_handlers
from services.simulator_service import run_simulation_cycle

socketio = SocketIO()


def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())

    logger = setup_logging(app)

    # --- MongoDB Atlas ---
    db = init_db(app)

    # --- Flask-Session persistida en MongoDB Atlas ---
    session_mongo_client = MongoClient(app.config["MONGO_URI"])
    app.config["SESSION_MONGODB"] = session_mongo_client
    app.config["SESSION_MONGODB_DB"] = app.config["MONGO_DB_NAME"]
    app.config["SESSION_MONGODB_COLLECT"] = app.config["SESSION_MONGO_COLLECTION"]
    Session(app)

    # --- CORS: permite acceso desde otros dispositivos de la red local ---
    cors_origins = app.config["CORS_ORIGINS"]
    origins = "*" if cors_origins == "*" else [o.strip() for o in cors_origins.split(",")]
    CORS(app, supports_credentials=True, origins=origins)

    # --- Swagger / OpenAPI ---
    app.config["SWAGGER"] = app.config["SWAGGER"]
    Swagger(app, config={
        "headers": [],
        "specs": [{
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/docs/",
    })

    # --- Blueprints ---
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(device_bp)
    app.register_blueprint(dashboard_bp)

    @app.route("/")
    def index():
        return redirect("/docs/")

    @app.route("/healthz")
    def healthz():
        return {"status": "ok", "service": "health-monitor-api"}, 200

    # --- Manejo global de errores ---
    register_error_handlers(app)

    # --- SocketIO ---
    socketio.init_app(
        app,
        cors_allowed_origins=origins,
        async_mode="eventlet",
        manage_session=True,
    )
    register_socket_handlers(socketio)

    _start_simulation_background_task(app, logger)

    return app


def _start_simulation_background_task(app, logger):
    """Lanza el hilo en segundo plano que genera datos biométricos
    simulados cada SIMULATION_INTERVAL_SECONDS para todos los usuarios
    conectados por WebSocket."""

    interval = app.config["SIMULATION_INTERVAL_SECONDS"]

    def _loop():
        logger.info("Simulador de métricas biométricas iniciado (cada %ss).", interval)
        while True:
            socketio.sleep(interval)
            with app.app_context():
                run_simulation_cycle(socketio)

    socketio.start_background_task(_loop)


app = create_app()


if __name__ == "__main__":
    host = app.config["HOST"]
    port = app.config["PORT"]
    logging.getLogger("health_monitor").info(
        "Servidor disponible en la red local: http://%s:%s (Swagger: /docs/)",
        host, port,
    )
    socketio.run(app, host=host, port=port, debug=app.config["DEBUG"], use_reloader=False)
