"""
utils/decorators.py
--------------------
Decoradores reutilizables, principalmente para proteger rutas que
requieren una sesión de usuario activa (autenticación basada en
sesiones de servidor, sin JWT).
"""

from functools import wraps
from flask import session
from utils.error_handlers import AuthenticationError


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
