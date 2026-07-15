"""
utils/decorators.py
--------------------
Decoradores reutilizables, principalmente para proteger rutas que
requieren una sesión de usuario activa (autenticación basada en
sesiones de servidor, sin JWT).
"""

from functools import wraps
from flask import session
from utils.error_handlers import AuthenticationError, AuthorizationError


def login_required(f):
    """
    Protege una ruta exigiendo que exista un 'user_id' válido en la
    sesión de servidor (persistida en MongoDB Atlas vía Flask-Session).
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            raise AuthenticationError(
                "Debes iniciar sesión para acceder a este recurso."
            )
        return f(*args, **kwargs)

    return decorated


def admin_required(f):
    """
    Protege una ruta exigiendo sesión activa Y rol 'admin'. Se apoya en
    'role' guardado en la sesión al iniciar sesión (ver auth_service.login_user),
    por lo que no requiere una consulta adicional a la base de datos en
    cada petición.
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            raise AuthenticationError(
                "Debes iniciar sesión para acceder a este recurso."
            )
        if session.get("role") != "admin":
            raise AuthorizationError(
                "Este recurso requiere privilegios de administrador."
            )
        return f(*args, **kwargs)

    return decorated
