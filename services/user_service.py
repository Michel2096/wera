"""
services/user_service.py
--------------------------
Lógica de negocio para consultar y actualizar el perfil del usuario
autenticado.
"""

from bson import ObjectId
from database.mongo import users_collection
from models.user import serialize_user
from utils.error_handlers import NotFoundError
from utils.logger import log_activity


def get_profile(user_id: str) -> dict:
    user_doc = users_collection().find_one({"_id": ObjectId(user_id)})
    if not user_doc:
        raise NotFoundError("Usuario no encontrado.")
    return serialize_user(user_doc)


def update_profile(user_id: str, data: dict) -> dict:
    update_fields = {}

    if "name" in data and data["name"]:
        update_fields["name"] = data["name"].strip()
    if "birth_date" in data:
        update_fields["birth_date"] = data["birth_date"]
    if "gender" in data:
        update_fields["gender"] = data["gender"]
    if "weight" in data and data["weight"] is not None:
        update_fields["weight"] = float(data["weight"])
    if "height" in data and data["height"] is not None:
        update_fields["height"] = float(data["height"])

    if not update_fields:
        return get_profile(user_id)

    result = users_collection().find_one_and_update(
        {"_id": ObjectId(user_id)},
        {"$set": update_fields},
        return_document=True,
    )

    if not result:
        raise NotFoundError("Usuario no encontrado.")

    log_activity(user_id, "profile_updated", extra=list(update_fields.keys()))

    return serialize_user(result)
