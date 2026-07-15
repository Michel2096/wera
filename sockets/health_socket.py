"""
sockets/health_socket.py
---------------------------
Eventos de Flask-SocketIO para sincronización en tiempo real de datos
biométricos. La autenticación del socket se apoya en la MISMA sesión de
servidor usada por la API REST (cookie de sesión compartida), por lo que
no se requiere ningún token adicional.

Cada usuario se une a una "room" privada = su user_id, así que solo
recibe eventos con sus propios datos.
"""

import logging
from flask import request, session
from flask_socketio import join_room, leave_room, emit

from services.simulator_service import register_connection, unregister_connection

logger = logging.getLogger("health_monitor.socket")


def register_socket_handlers(socketio):

    @socketio.on("connect")
    def handle_connect():
        user_id = session.get("user_id")
        if not user_id:
            logger.warning("Conexión de socket rechazada: sin sesión activa.")
            emit("connection_error", {"message": "No autenticado. Inicia sesión antes de conectar."})
            return False  # rechaza el handshake

        join_room(user_id)
        register_connection(user_id, request.sid)
        emit("connection_ack", {"message": "Conectado a sincronización en tiempo real.", "user_id": user_id})
        logger.info("Socket conectado para user_id=%s sid=%s", user_id, request.sid)

    @socketio.on("disconnect")
    def handle_disconnect():
        user_id = session.get("user_id")
        if user_id:
            leave_room(user_id)
            unregister_connection(user_id, request.sid)

    @socketio.on("ping_server")
    def handle_ping():
        emit("pong_server", {"message": "pong"})
