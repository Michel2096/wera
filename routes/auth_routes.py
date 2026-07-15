
from flask import Blueprint, request, current_app
from utils.responses import success_response
from utils.error_handlers import ValidationError
from utils.validators import validate_register_payload, validate_login_payload
from services import auth_service

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Registrar un nuevo usuario
    ---
    tags:
      - Auth
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [name, email, password]
          properties:
            name: {type: string, example: "Taurus López"}
            email: {type: string, example: "taurus@example.com"}
            password: {type: string, example: "SuperSecret123"}
            birth_date: {type: string, example: "2000-05-14"}
            gender: {type: string, enum: [male, female, other]}
            weight: {type: number, example: 70.5}
            height: {type: number, example: 175}
    responses:
      201:
        description: Usuario creado exitosamente
      409:
        description: El correo ya está registrado
      422:
        description: Error de validación
    """
    data = request.get_json(silent=True) or {}
    errors = validate_register_payload(data)
    if errors:
        raise ValidationError("Datos de registro inválidos.", errors=errors)

    user = auth_service.register_user(data, current_app.config["BCRYPT_ROUNDS"])
    return success_response("Usuario registrado exitosamente.", data=user, status_code=201)


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Iniciar sesión
    ---
    tags:
      - Auth
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [email, password]
          properties:
            email: {type: string, example: "taurus@example.com"}
            password: {type: string, example: "SuperSecret123"}
    responses:
      200:
        description: Sesión iniciada. Se establece una cookie de sesión segura.
      401:
        description: Credenciales inválidas
      422:
        description: Error de validación
    """
    data = request.get_json(silent=True) or {}
    errors = validate_login_payload(data)
    if errors:
        raise ValidationError("Datos de inicio de sesión inválidos.", errors=errors)

    user = auth_service.login_user(data)
    return success_response("Sesión iniciada exitosamente.", data=user)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """
    Cerrar sesión
    ---
    tags:
      - Auth
    responses:
      200:
        description: Sesión cerrada exitosamente
    """
    auth_service.logout_user()
    return success_response("Sesión cerrada exitosamente.")


@auth_bp.route("/session", methods=["GET"])
def get_session():
    """
    Consultar el estado de la sesión actual
    ---
    tags:
      - Auth
    responses:
      200:
        description: Información de la sesión activa
      401:
        description: No hay sesión activa
    """
    result = auth_service.get_current_session()
    return success_response("Sesión activa.", data=result)
