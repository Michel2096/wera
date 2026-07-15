"""
routes/device_routes.py
--------------------------
Endpoints:
  POST /device/connect      -> conexión directa (con sesión) O
                                 vinculación vía QR o código corto
                                 (con qr_token o pairing_code, sin sesión)
  GET  /device/list         -> requiere sesión
  POST /device/disconnect   -> requiere sesión
  GET  /device/qr           -> requiere sesión; genera QR temporal
"""

from flask import Blueprint, request, session, current_app
from utils.responses import success_response
from utils.error_handlers import ValidationError, AuthenticationError
from utils.validators import validate_device_connect_payload, validate_qr_scan_payload
from utils.decorators import login_required
from services import device_service, qr_service

device_bp = Blueprint("device", __name__, url_prefix="/device")


@device_bp.route("/connect", methods=["POST"])
def connect_device():
    """
    Conectar un dispositivo (directamente o mediante escaneo de QR)
    ---
    tags:
      - Devices
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        description: >
          Envía 'qr_token' cuando un reloj inteligente escanea un código QR,
          o 'pairing_code' cuando la persona escribe a mano el código corto
          en vez de escanear (ninguno requiere sesión de navegador). Omite
          ambos y usa la sesión activa para conectar un dispositivo
          directamente (p. ej. la app del propio usuario).
        schema:
          type: object
          properties:
            qr_token: {type: string}
            pairing_code: {type: string, example: "482913"}
            device_name: {type: string, example: "Reloj de Taurus"}
            device_type: {type: string, enum: [watch, phone, wearable]}
    responses:
      201:
        description: Dispositivo conectado exitosamente
      401:
        description: No autenticado (solo aplica al flujo directo, sin qr_token)
      404:
        description: Código QR inválido o ya utilizado
      409:
        description: El código QR expiró o el dispositivo ya existe
      422:
        description: Error de validación
    """
    data = request.get_json(silent=True) or {}

    if data.get("qr_token") or data.get("pairing_code"):
        errors = validate_qr_scan_payload(data)
        if errors:
            raise ValidationError("Datos de vinculación inválidos.", errors=errors)

        device = qr_service.redeem_qr_token(
            qr_token=data.get("qr_token"),
            pairing_code=data.get("pairing_code"),
            device_name=data["device_name"],
            device_type=data.get("device_type", "watch"),
        )
        return success_response("Dispositivo vinculado exitosamente.", data=device, status_code=201)

    # Flujo directo: requiere sesión activa
    if not session.get("user_id"):
        raise AuthenticationError(
            "Debes iniciar sesión para conectar un dispositivo directamente, "
            "o enviar 'qr_token' si estás vinculando vía código QR."
        )

    errors = validate_device_connect_payload(data)
    if errors:
        raise ValidationError("Datos de dispositivo inválidos.", errors=errors)

    device = device_service.connect_device_directly(
        user_id=session["user_id"],
        device_name=data["device_name"],
        device_type=data["device_type"],
    )
    return success_response("Dispositivo conectado exitosamente.", data=device, status_code=201)


@device_bp.route("/list", methods=["GET"])
@login_required
def list_devices():
    """
    Listar los dispositivos del usuario autenticado
    ---
    tags:
      - Devices
    responses:
      200:
        description: Lista de dispositivos asociados a la cuenta
      401:
        description: No autenticado
    """
    devices = device_service.list_devices(session["user_id"])
    return success_response("Dispositivos obtenidos exitosamente.", data=devices)


@device_bp.route("/disconnect", methods=["POST"])
@login_required
def disconnect_device():
    """
    Desconectar un dispositivo
    ---
    tags:
      - Devices
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [device_id]
          properties:
            device_id: {type: string}
    responses:
      200:
        description: Dispositivo desconectado exitosamente
      401:
        description: No autenticado
      404:
        description: Dispositivo no encontrado
    """
    data = request.get_json(silent=True) or {}
    device_id = data.get("device_id")
    if not device_id:
        raise ValidationError("El campo 'device_id' es obligatorio.")

    device = device_service.disconnect_device(session["user_id"], device_id)
    return success_response("Dispositivo desconectado exitosamente.", data=device)


@device_bp.route("/qr", methods=["GET"])
@login_required
def get_device_qr():
    """
    Generar un código QR temporal para vincular un reloj inteligente
    ---
    tags:
      - Devices
    responses:
      200:
        description: Código QR generado (imagen base64) y token temporal
      401:
        description: No autenticado
    """
    result = qr_service.generate_device_qr(
        session["user_id"], current_app.config["QR_TOKEN_EXPIRATION_SECONDS"]
    )
    return success_response("Código QR generado exitosamente.", data=result)
