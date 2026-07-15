"""
routes/dashboard_routes.py
------------------------------
Endpoint:
  GET /dashboard

Agrega en una sola respuesta la información más relevante del usuario:
perfil, dispositivos conectados, última métrica biométrica y
estadísticas, pensado para pintar la pantalla principal de la app
(estilo Huawei Health) en una sola petición.
"""

from flask import Blueprint, session
from utils.responses import success_response
from utils.decorators import login_required
from services import user_service, device_service, health_service

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("", methods=["GET"])
@login_required
def get_dashboard():
    """
    Obtener el resumen del dashboard principal
    ---
    tags:
      - Dashboard
    responses:
      200:
        description: Resumen consolidado (perfil, dispositivos, métrica actual, estadísticas)
      401:
        description: No autenticado
    """
    user_id = session["user_id"]

    profile = user_service.get_profile(user_id)
    devices = device_service.list_devices(user_id)
    statistics = health_service.get_statistics(user_id)

    try:
        current_metric = health_service.get_current_metric(user_id)
    except Exception:
        current_metric = None

    connected_devices = [d for d in devices if d["status"] == "connected"]

    return success_response(
        "Dashboard obtenido exitosamente.",
        data={
            "profile": profile,
            "devices": devices,
            "connected_devices_count": len(connected_devices),
            "current_metric": current_metric,
            "statistics": statistics,
        },
    )
