"""
tests/conftest.py
--------------------
Fixtures compartidos para pruebas unitarias. Se usa `mongomock` para
simular MongoDB Atlas sin necesidad de una conexión real, y se ejecutan
las pruebas directamente contra la capa de servicios (unit tests puros),
evitando levantar Flask-SocketIO/eventlet.
"""

import sys
import os
import pytest
import mongomock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import database.mongo as mongo_module


@pytest.fixture(autouse=True)
def fake_db(monkeypatch):
    """Reemplaza la base de datos real por una base de datos en memoria
    (mongomock) para cada prueba, garantizando aislamiento entre tests."""
    client = mongomock.MongoClient()
    db = client["health_monitor_test_db"]

    monkeypatch.setattr(mongo_module, "_db", db)
    monkeypatch.setattr(mongo_module, "_client", client)

    yield db


class FakeSession(dict):
    """Sustituto simple de flask.session (dict + atributo 'permanent')."""
    permanent = False


@pytest.fixture
def flask_session(monkeypatch):
    """Simula flask.session para probar servicios que dependen de ella,
    parcheando la referencia ya importada en cada módulo de servicio."""
    fake_session = FakeSession()

    import services.auth_service as auth_service_module
    monkeypatch.setattr(auth_service_module, "session", fake_session)

    return fake_session
