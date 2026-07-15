"""
utils/error_handlers.py
------------------------
Excepciones de dominio personalizadas y registro de manejadores
globales de error para la aplicación Flask.
"""

import logging
from werkzeug.exceptions import HTTPException
from pymongo.errors import PyMongoError
from utils.responses import error_response

logger = logging.getLogger("health_monitor.errors")


class APIError(Exception):
    """Excepción base para errores de negocio controlados."""

    def __init__(self, message, status_code=400, errors=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.errors = errors


class ValidationError(APIError):
    def __init__(self, message="Error de validación", errors=None):
        super().__init__(message, status_code=422, errors=errors)


class AuthenticationError(APIError):
    def __init__(self, message="No autenticado"):
        super().__init__(message, status_code=401)


class AuthorizationError(APIError):
    def __init__(self, message="No autorizado"):
        super().__init__(message, status_code=403)


class NotFoundError(APIError):
    def __init__(self, message="Recurso no encontrado"):
        super().__init__(message, status_code=404)


class ConflictError(APIError):
    def __init__(self, message="Conflicto con el estado actual del recurso"):
        super().__init__(message, status_code=409)


def register_error_handlers(app):
    """Registra manejadores globales de error en la instancia Flask."""

    @app.errorhandler(APIError)
    def handle_api_error(err):
        logger.warning("APIError: %s", err.message)
        return error_response(err.message, err.status_code, err.errors)

    @app.errorhandler(HTTPException)
    def handle_http_error(err):
        logger.warning("HTTPException: %s", err)
        return error_response(err.description, err.code)

    @app.errorhandler(PyMongoError)
    def handle_mongo_error(err):
        logger.error("Error de MongoDB: %s", err)
        return error_response(
            "Error interno de base de datos. Intenta nuevamente más tarde.", 500
        )

    @app.errorhandler(Exception)
    def handle_uncaught_error(err):
        logger.exception("Error no controlado: %s", err)
        return error_response("Error interno del servidor.", 500)

    @app.errorhandler(404)
    def handle_404(err):
        return error_response("Ruta no encontrada.", 404)

    @app.errorhandler(405)
    def handle_405(err):
        return error_response("Método HTTP no permitido para esta ruta.", 405)
