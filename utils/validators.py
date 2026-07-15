"""
utils/validators.py
--------------------
Validaciones de payloads de entrada para cada módulo de la API.
Cada función retorna una lista de errores (vacía si todo es válido).
"""

import re
from datetime import datetime

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_register_payload(data: dict) -> list:
    errors = []
    if not data:
        return ["El cuerpo de la solicitud está vacío."]

    name = data.get("name", "")
    email = data.get("email", "")
    password = data.get("password", "")

    if not name or len(name.strip()) < 2:
        errors.append("El campo 'name' es obligatorio (mínimo 2 caracteres).")

    if not email or not EMAIL_REGEX.match(email):
        errors.append("El campo 'email' es obligatorio y debe tener formato válido.")

    if not password or len(password) < 8:
        errors.append("El campo 'password' es obligatorio (mínimo 8 caracteres).")

    birth_date = data.get("birth_date")
    if birth_date:
        try:
            datetime.strptime(birth_date, "%Y-%m-%d")
        except ValueError:
            errors.append("El campo 'birth_date' debe tener formato YYYY-MM-DD.")

    gender = data.get("gender")
    if gender and gender not in ("male", "female", "other"):
        errors.append("El campo 'gender' debe ser 'male', 'female' u 'other'.")

    for numeric_field in ("weight", "height"):
        value = data.get(numeric_field)
        if value is not None:
            try:
                float(value)
            except (TypeError, ValueError):
                errors.append(f"El campo '{numeric_field}' debe ser numérico.")

    return errors


def validate_login_payload(data: dict) -> list:
    errors = []
    if not data:
        return ["El cuerpo de la solicitud está vacío."]

    if not data.get("email") or not EMAIL_REGEX.match(data.get("email", "")):
        errors.append("El campo 'email' es obligatorio y debe tener formato válido.")

    if not data.get("password"):
        errors.append("El campo 'password' es obligatorio.")

    return errors


def validate_profile_update_payload(data: dict) -> list:
    errors = []
    if not data:
        return ["El cuerpo de la solicitud está vacío."]

    allowed_fields = {"name", "birth_date", "gender", "weight", "height"}
    unknown = set(data.keys()) - allowed_fields
    if unknown:
        errors.append(f"Campos no permitidos: {', '.join(unknown)}")

    if "birth_date" in data and data["birth_date"]:
        try:
            datetime.strptime(data["birth_date"], "%Y-%m-%d")
        except ValueError:
            errors.append("El campo 'birth_date' debe tener formato YYYY-MM-DD.")

    if "gender" in data and data["gender"] not in (None, "male", "female", "other"):
        errors.append("El campo 'gender' debe ser 'male', 'female' u 'other'.")

    for numeric_field in ("weight", "height"):
        if numeric_field in data and data[numeric_field] is not None:
            try:
                float(data[numeric_field])
            except (TypeError, ValueError):
                errors.append(f"El campo '{numeric_field}' debe ser numérico.")

    return errors


def validate_device_connect_payload(data: dict) -> list:
    errors = []
    if not data:
        return ["El cuerpo de la solicitud está vacío."]

    device_type = data.get("device_type")
    if device_type not in ("watch", "phone", "wearable"):
        errors.append(
            "El campo 'device_type' debe ser 'watch', 'phone' o 'wearable'."
        )

    device_name = data.get("device_name")
    if not device_name or len(device_name.strip()) < 2:
        errors.append("El campo 'device_name' es obligatorio (mínimo 2 caracteres).")

    return errors


def validate_qr_scan_payload(data: dict) -> list:
    errors = []
    if not data:
        return ["El cuerpo de la solicitud está vacío."]

    if not data.get("qr_token") and not data.get("pairing_code"):
        errors.append("Debes enviar 'qr_token' o 'pairing_code'.")

    if not data.get("device_name"):
        errors.append("El campo 'device_name' es obligatorio.")

    if data.get("device_type") not in (None, "watch", "phone", "wearable"):
        errors.append("El campo 'device_type' debe ser 'watch', 'phone' o 'wearable'.")

    return errors


def validate_pagination_params(page, limit):
    errors = []
    try:
        page = int(page)
        if page < 1:
            errors.append("El parámetro 'page' debe ser mayor o igual a 1.")
    except (TypeError, ValueError):
        errors.append("El parámetro 'page' debe ser un entero.")

    try:
        limit = int(limit)
        if limit < 1 or limit > 200:
            errors.append("El parámetro 'limit' debe estar entre 1 y 200.")
    except (TypeError, ValueError):
        errors.append("El parámetro 'limit' debe ser un entero.")

    return errors
