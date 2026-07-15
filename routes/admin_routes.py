
from flask import Blueprint, request, session, current_app
from utils.responses import success_response
from utils.error_handlers import ValidationError
from utils.validators import (
    validate_admin_create_user_payload,
    validate_admin_update_user_payload,
    validate_role_payload,
    validate_pagination_params,
)
from utils.decorators import login_required, admin_required
from services import admin_service

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# --- CRUD de usuarios ---

@admin_bp.route("/users", methods=["GET"])
@login_required
@admin_required
def list_users():
    """
    Listar usuarios (con búsqueda, filtros y paginación)
    ---
    tags:
      - Admin - Usuarios
    security:
      - cookieAuth: []
    parameters:
      - in: query
        name: page
        type: integer
        default: 1
      - in: query
        name: limit
        type: integer
        default: 50
      - in: query
        name: search
        type: string
        description: Busca por nombre o correo (coincidencia parcial)
      - in: query
        name: role
        type: string
        enum: [user, admin]
      - in: query
        name: is_active
        type: boolean
    responses:
      200:
        description: Lista paginada de usuarios
      401:
        description: No autenticado
      403:
        description: Requiere privilegios de administrador
      422:
        description: Parámetros de paginación inválidos
    """
    page = request.args.get("page", 1)
    limit = request.args.get("limit", 50)

    errors = validate_pagination_params(page, limit)
    if errors:
        raise ValidationError("Parámetros de paginación inválidos.", errors=errors)

    search = request.args.get("search")
    role = request.args.get("role")

    is_active_raw = request.args.get("is_active")
    is_active = None
    if is_active_raw is not None:
        is_active = is_active_raw.strip().lower() in ("1", "true", "yes")

    result = admin_service.list_users(
        page=int(page), limit=int(limit), search=search, role=role, is_active=is_active,
    )
    return success_response("Usuarios obtenidos exitosamente.", data=result)


@admin_bp.route("/users/<user_id>", methods=["GET"])
@login_required
@admin_required
def get_user(user_id):
    """
    Obtener un usuario por ID
    ---
    tags:
      - Admin - Usuarios
    security:
      - cookieAuth: []
    parameters:
      - in: path
        name: user_id
        type: string
        required: true
    responses:
      200:
        description: Usuario encontrado
      401:
        description: No autenticado
      403:
        description: Requiere privilegios de administrador
      404:
        description: Usuario no encontrado
    """
    user = admin_service.get_user(user_id)
    return success_response("Usuario obtenido exitosamente.", data=user)


@admin_bp.route("/users", methods=["POST"])
@login_required
@admin_required
def create_user():
    """
    Crear un nuevo usuario (permite asignar rol directamente)
    ---
    tags:
      - Admin - Usuarios
    security:
      - cookieAuth: []
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
            name: {type: string, example: "Ana Torres"}
            email: {type: string, example: "ana@example.com"}
            password: {type: string, example: "SuperSecret123"}
            birth_date: {type: string, example: "1998-03-20"}
            gender: {type: string, enum: [male, female, other]}
            weight: {type: number, example: 60}
            height: {type: number, example: 165}
            role: {type: string, enum: [user, admin], default: user}
            is_active: {type: boolean, default: true}
    responses:
      201:
        description: Usuario creado exitosamente
      401:
        description: No autenticado
      403:
        description: Requiere privilegios de administrador
      409:
        description: El correo ya está registrado
      422:
        description: Error de validación
    """
    data = request.get_json(silent=True) or {}
    errors = validate_admin_create_user_payload(data)
    if errors:
        raise ValidationError("Datos de usuario inválidos.", errors=errors)

    user = admin_service.create_user(
        data, current_app.config["BCRYPT_ROUNDS"], actor_id=session.get("user_id"),
    )
    return success_response("Usuario creado exitosamente.", data=user, status_code=201)


@admin_bp.route("/users/<user_id>", methods=["PUT"])
@login_required
@admin_required
def update_user(user_id):
    """
    Actualizar un usuario (perfil, credenciales, rol o estado)
    ---
    tags:
      - Admin - Usuarios
    security:
      - cookieAuth: []
    consumes:
      - application/json
    parameters:
      - in: path
        name: user_id
        type: string
        required: true
      - in: body
        name: body
        schema:
          type: object
          properties:
            name: {type: string}
            email: {type: string}
            password: {type: string, description: "Opcional, mínimo 8 caracteres"}
            birth_date: {type: string, example: "2000-05-14"}
            gender: {type: string, enum: [male, female, other]}
            weight: {type: number}
            height: {type: number}
            role: {type: string, enum: [user, admin]}
            is_active: {type: boolean}
    responses:
      200:
        description: Usuario actualizado exitosamente
      401:
        description: No autenticado
      403:
        description: Requiere privilegios de administrador
      404:
        description: Usuario no encontrado
      409:
        description: Correo en uso o operación bloqueada por regla de último administrador
      422:
        description: Error de validación
    """
    data = request.get_json(silent=True) or {}
    errors = validate_admin_update_user_payload(data)
    if errors:
        raise ValidationError("Datos de usuario inválidos.", errors=errors)

    user = admin_service.update_user(
        user_id, data, current_app.config["BCRYPT_ROUNDS"], actor_id=session.get("user_id"),
    )
    return success_response("Usuario actualizado exitosamente.", data=user)


@admin_bp.route("/users/<user_id>/role", methods=["PATCH"])
@login_required
@admin_required
def update_user_role(user_id):
    """
    Cambiar el rol de un usuario (atajo rápido)
    ---
    tags:
      - Admin - Usuarios
    security:
      - cookieAuth: []
    consumes:
      - application/json
    parameters:
      - in: path
        name: user_id
        type: string
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [role]
          properties:
            role: {type: string, enum: [user, admin]}
    responses:
      200:
        description: Rol actualizado exitosamente
      401:
        description: No autenticado
      403:
        description: Requiere privilegios de administrador
      404:
        description: Usuario no encontrado
      409:
        description: No se puede quitar el rol al último administrador
      422:
        description: Error de validación
    """
    data = request.get_json(silent=True) or {}
    errors = validate_role_payload(data)
    if errors:
        raise ValidationError("Datos de rol inválidos.", errors=errors)

    user = admin_service.update_user_role(user_id, data["role"], actor_id=session.get("user_id"))
    return success_response("Rol actualizado exitosamente.", data=user)


@admin_bp.route("/users/<user_id>", methods=["DELETE"])
@login_required
@admin_required
def delete_user(user_id):
    """
    Eliminar un usuario (y sus datos asociados: dispositivos, métricas y auditoría)
    ---
    tags:
      - Admin - Usuarios
    security:
      - cookieAuth: []
    parameters:
      - in: path
        name: user_id
        type: string
        required: true
    responses:
      200:
        description: Usuario eliminado exitosamente
      401:
        description: No autenticado
      403:
        description: Requiere privilegios de administrador
      404:
        description: Usuario no encontrado
      409:
        description: No se puede eliminar al último administrador
    """
    admin_service.delete_user(user_id, actor_id=session.get("user_id"))
    return success_response("Usuario eliminado exitosamente.")


# --- Estadísticas ---

@admin_bp.route("/statistics", methods=["GET"])
@login_required
@admin_required
def platform_statistics():
    """
    Obtener estadísticas globales de la plataforma
    ---
    tags:
      - Admin - Estadísticas
    security:
      - cookieAuth: []
    responses:
      200:
        description: >
          Estadísticas agregadas de usuarios (totales, por rol, por género,
          altas recientes), dispositivos (por estado y tipo), métricas
          biométricas (totales y promedios de la plataforma) y auditoría.
      401:
        description: No autenticado
      403:
        description: Requiere privilegios de administrador
    """
    stats = admin_service.get_platform_statistics()
    return success_response("Estadísticas obtenidas exitosamente.", data=stats)


@admin_bp.route("/statistics/users/growth", methods=["GET"])
@login_required
@admin_required
def user_growth_statistics():
    """
    Obtener el crecimiento de usuarios registrados por día
    ---
    tags:
      - Admin - Estadísticas
    security:
      - cookieAuth: []
    parameters:
      - in: query
        name: days
        type: integer
        default: 30
        description: Ventana de tiempo en días hacia atrás desde hoy
    responses:
      200:
        description: Serie temporal de altas de usuarios por día
      401:
        description: No autenticado
      403:
        description: Requiere privilegios de administrador
      422:
        description: El parámetro 'days' debe ser un entero positivo
    """
    days_raw = request.args.get("days", 30)
    try:
        days = int(days_raw)
        if days < 1 or days > 365:
            raise ValueError
    except (TypeError, ValueError):
        raise ValidationError("El parámetro 'days' debe ser un entero entre 1 y 365.")

    growth = admin_service.get_user_growth(days)
    return success_response("Crecimiento de usuarios obtenido exitosamente.", data=growth)


# --- Auditoría ---

@admin_bp.route("/activity-logs", methods=["GET"])
@login_required
@admin_required
def activity_logs():
    """
    Listar el registro de auditoría de actividad (paginado)
    ---
    tags:
      - Admin - Estadísticas
    security:
      - cookieAuth: []
    parameters:
      - in: query
        name: page
        type: integer
        default: 1
      - in: query
        name: limit
        type: integer
        default: 50
      - in: query
        name: user_id
        type: string
        description: Filtra por usuario específico
      - in: query
        name: action
        type: string
        description: "Filtra por tipo de acción, p. ej. 'user_login', 'admin_user_updated'"
    responses:
      200:
        description: Lista paginada de eventos de auditoría
      401:
        description: No autenticado
      403:
        description: Requiere privilegios de administrador
      422:
        description: Parámetros de paginación inválidos
    """
    page = request.args.get("page", 1)
    limit = request.args.get("limit", 50)

    errors = validate_pagination_params(page, limit)
    if errors:
        raise ValidationError("Parámetros de paginación inválidos.", errors=errors)

    result = admin_service.list_activity_logs(
        page=int(page),
        limit=int(limit),
        user_id=request.args.get("user_id"),
        action=request.args.get("action"),
    )
    return success_response("Registro de auditoría obtenido exitosamente.", data=result)
