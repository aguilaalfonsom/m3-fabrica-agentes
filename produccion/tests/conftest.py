"""Las pruebas corren con LLM_FALSO=1: sin red, sin credenciales y deterministas (así corren en CI)."""
import os
import tempfile

os.environ.update({
    "LLM_FALSO": "1", "LANGSMITH_TRACING": "false", "API_KEYS": "cliente:llave-cliente-prueba,lector:llave-lector-prueba",
    "DIR_DATOS": tempfile.mkdtemp(prefix="fabrica-pruebas-"), "LIMITE_POR_MINUTO": "1000", "MAX_CONCURRENCIA": "4",
})

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from produccion.api import app  # noqa: E402

CLIENTE = {"X-API-Key": "llave-cliente-prueba"}
LECTOR = {"X-API-Key": "llave-lector-prueba"}


@pytest.fixture(scope="session")
def api():
    with TestClient(app) as c:
        yield c
