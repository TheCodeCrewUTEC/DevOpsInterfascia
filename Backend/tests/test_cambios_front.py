from fastapi.testclient import TestClient

from app.main import app
from app.services import cache_service
from app.services.dato_validado_service import clave_campo


def test_clave_campo_ignora_tildes_mayusculas_y_asteriscos():
    assert clave_campo("Nombre del proyecto *") == "nombre del proyecto"
    assert clave_campo("NOMBRE DEL PROYECTO:") == "nombre del proyecto"
    assert clave_campo("Institución  responsable") == "institucion responsable"


def test_cache_sin_redis_no_falla(monkeypatch):
    monkeypatch.delenv("REDIS_HOST", raising=False)
    clave = cache_service.clave("prueba", {"page": 1})

    cache_service.guardar(clave, {"items": []})
    assert cache_service.leer(clave) is None


def test_metrics_expone_prometheus():
    # Sin context manager: no corre el lifespan (que necesita la base)
    response = TestClient(app).get("/metrics")

    assert response.status_code == 200
    assert "http_requests_total" in response.text or "# HELP" in response.text
