"""
routes/profile_routes.py
---------------------------
Endpoints:
  GET /profile
  PUT /profile
"""

from flask import Blueprint, request, session
from utils.responses import success_response
from utils.error_handlers import ValidationError
from utils.validators import validate_profile_update_payload
from utils.decorators import login_required
from services import user_service

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


@profile_bp.route("", methods=["GET"])
@login_required
def get_profile():
    """
    Obtener el perfil del usuario autenticado
    ---
    tags:
      - Profile
    responses:
      200:
        description: Perfil del usuario
      401:
        description: No autenticado
    """
    profile = user_service.get_profile(session["user_id"])
    return success_response("Perfil obtenido exitosamente.", data=profile)


@profile_bp.route("", methods=["PUT"])
@login_required
def update_profile():
    """
    Actualizar el perfil del usuario autenticado
    ---
    tags:
      - Profile
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        schema:
          type: object
          properties:
            name: {type: string}
            birth_date: {type: string, example: "2000-05-14"}
            gender: {type: string, enum: [male, female, other]}
            weight: {type: number}
            height: {type: number}
    responses:
      200:
        description: Perfil actualizado exitosamente
      401:
        description: No autenticado
      422:
        description: Error de validación
    """
    data = request.get_json(silent=True) or {}
    errors = validate_profile_update_payload(data)
    if errors:
        raise ValidationError("Datos de perfil inválidos.", errors=errors)

    updated = user_service.update_profile(session["user_id"], data)
    return success_response("Perfil actualizado exitosamente.", data=updated)
