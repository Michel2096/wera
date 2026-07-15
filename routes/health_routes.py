"""
routes/health_routes.py
--------------------------
Endpoints:
  GET /health/current
  GET /health/history
  GET /health/statistics
"""

from flask import Blueprint, request, session
from utils.responses import success_response
from utils.error_handlers import ValidationError
from utils.validators import validate_pagination_params
from utils.decorators import login_required
from services import health_service

health_bp = Blueprint("health", __name__, url_prefix="/health")


@health_bp.route("/current", methods=["GET"])
@login_required
def current_metric():
    """
    Obtener la última lectura biométrica del usuario
    ---
    tags:
      - Health Metrics
    responses:
      200:
        description: Última métrica biométrica registrada
      401:
        description: No autenticado
      404:
        description: Aún no hay métricas registradas
    """
    metric = health_service.get_current_metric(session["user_id"])
    return success_response("Métrica actual obtenida.", data=metric)


@health_bp.route("/history", methods=["GET"])
@login_required
def history():
    """
    Obtener el historial paginado de métricas biométricas
    ---
    tags:
      - Health Metrics
    parameters:
      - in: query
        name: page
        type: integer
        default: 1
      - in: query
        name: limit
        type: integer
        default: 50
    responses:
      200:
        description: Historial de métricas biométricas
      401:
        description: No autenticado
      422:
        description: Parámetros de paginación inválidos
    """
    page = request.args.get("page", 1)
    limit = request.args.get("limit", 50)

    errors = validate_pagination_params(page, limit)
    if errors:
        raise ValidationError("Parámetros de paginación inválidos.", errors=errors)

    result = health_service.get_history(session["user_id"], int(page), int(limit))
    return success_response("Historial obtenido exitosamente.", data=result)


@health_bp.route("/statistics", methods=["GET"])
@login_required
def statistics():
    """
    Obtener estadísticas agregadas de las métricas biométricas
    ---
    tags:
      - Health Metrics
    responses:
      200:
        description: Estadísticas agregadas (promedios, mínimos, máximos, totales)
      401:
        description: No autenticado
    """
    stats = health_service.get_statistics(session["user_id"])
    return success_response("Estadísticas obtenidas exitosamente.", data=stats)
