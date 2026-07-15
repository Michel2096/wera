"""
utils/responses.py
-------------------
Formato de respuesta JSON consistente en toda la API.
"""

from flask import jsonify


def success_response(message="OK", data=None, status_code=200, meta=None):
    body = {"success": True, "message": message}
    if data is not None:
        body["data"] = data
    if meta is not None:
        body["meta"] = meta
    return jsonify(body), status_code


def error_response(message="Ha ocurrido un error", status_code=400, errors=None):
    body = {"success": False, "message": message}
    if errors is not None:
        body["errors"] = errors
    return jsonify(body), status_code
