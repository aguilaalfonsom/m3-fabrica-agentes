"""Pruebas de la API de producción: operación, seguridad, costos, observabilidad y concurrencia."""
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from produccion.config import RAIZ, config
from produccion.contexto import contexto_para
from produccion.pii import enmascarar
from produccion.tests.conftest import CLIENTE, LECTOR

HU10 = (RAIZ / "historias" / "HU-10-solicitar-vacaciones.md").read_text(encoding="utf-8")
HU99 = (RAIZ / "historias" / "HU-99-envenenada.md").read_text(encoding="utf-8")


def historia_unica(extra: str = "") -> str:
    return f"# HU-02 · Directorio {uuid.uuid4().hex[:6]}\n\nComo persona de RH, quiero buscar empleados, para encontrarlos.{extra}"


# --- Operación ------------------------------------------------------------------------------
def test_health_es_publico(api):
    r = api.get("/health")
    assert r.status_code == 200 and r.json()["estado"] == "ok"
    assert "X-Request-ID" in r.headers and r.headers["X-Content-Type-Options"] == "nosniff"


def test_ready_reporta_checks_sin_secretos(api):
    r = api.get("/ready")
    assert r.status_code == 200 and r.json()["listo"] is True
    assert "llave" not in r.text.lower() or "llaves_configuradas" in r.text
    assert "llave-cliente-prueba" not in r.text


def test_openapi_documenta_endpoints_y_seguridad(api):
    spec = api.get("/openapi.json").json()
    assert {"/health", "/ready", "/v1/criterios", "/v1/metricas", "/metrics"} <= set(spec["paths"])
    assert "APIKeyHeader" in spec["components"]["securitySchemes"]


# --- Flujo de agentes ---------------------------------------------------------------------
def test_criterios_hu10_trae_gherkin_casos_y_costos(api):
    r = api.post("/v1/criterios", json={"historia": HU10}, headers=CLIENTE)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["hu"] == "HU-10" and cuerpo["gherkin"].startswith("# language: es")
    assert len(cuerpo["casos"]) == cuerpo["gherkin"].count("Escenario:")
    assert {a["agente"] for a in cuerpo["agentes"]} == {"filtro", "analista", "disenador"}
    assert cuerpo["request_id"] == r.headers["X-Request-ID"]


def test_ruteo_usa_modelo_barato_en_filtro_y_disenador(api):
    cuerpo = api.post("/v1/criterios", json={"historia": historia_unica()}, headers=CLIENTE).json()
    modelos = {a["agente"]: a["modelo"] for a in cuerpo["agentes"]}
    assert modelos["filtro"] == config().modelo_clasificador
    assert modelos["disenador"] == config().modelo_disenador
    assert modelos["analista"] == config().modelo_analista


def test_cache_segunda_peticion_cuesta_cero(api):
    h = historia_unica()
    primera = api.post("/v1/criterios", json={"historia": h}, headers=CLIENTE).json()
    segunda = api.post("/v1/criterios", json={"historia": h + "  \n"}, headers=CLIENTE).json()
    assert primera["desde_cache"] is False and segunda["desde_cache"] is True
    assert segunda["costo_usd"] == 0 and segunda["agentes"] == []
    assert segunda["gherkin"] == primera["gherkin"]


def test_presupuesto_por_peticion_corta_los_reintentos():
    from produccion.grafo import validar_criterios
    estado = {"gherkin": "texto sin gherkin", "hu": "HU-02", "intentos_analista": 1, "costo_usd": 999.0}
    assert validar_criterios(estado)["resultado"] == "presupuesto_excedido"
    estado["costo_usd"] = 0.0
    assert "resultado" not in validar_criterios(estado)          # con presupuesto, se reintenta


def test_contexto_recortado_es_mas_corto_y_conserva_la_hu():
    completo, recortado = contexto_para("HU-10", False), contexto_para("HU-10", True)
    assert len(recortado) < len(completo)
    assert "Reglas de vacaciones" in recortado and "## Puertos" not in recortado
    assert "Reglas de vacaciones" not in contexto_para("HU-02", True)


# --- Seguridad ----------------------------------------------------------------------------
def test_sin_llave_401_y_llave_invalida_401(api):
    assert api.post("/v1/criterios", json={"historia": HU10}).status_code == 401
    assert api.post("/v1/criterios", json={"historia": HU10}, headers={"X-API-Key": "x"}).status_code == 401


def test_minimo_privilegio_lector_no_genera_pero_ve_metricas(api):
    assert api.post("/v1/criterios", json={"historia": HU10}, headers=LECTOR).status_code == 403
    assert api.get("/v1/metricas", headers=LECTOR).status_code == 200


def test_validacion_de_entrada(api):
    assert api.post("/v1/criterios", json={"historia": "corto"}, headers=CLIENTE).status_code == 422
    assert api.post("/v1/criterios", json={"historia": "x" * 40}, headers=CLIENTE).status_code == 422
    assert api.post("/v1/criterios", json={"historia": historia_unica("\x00")}, headers=CLIENTE).status_code == 422
    largo = historia_unica("a" * (config().max_caracteres_historia + 10))
    assert api.post("/v1/criterios", json={"historia": largo}, headers=CLIENTE).status_code == 422


def test_error_422_no_refleja_la_entrada(api):
    r = api.post("/v1/criterios", json={"historia": "mi correo es juan.perez@gmail.com" + "x" * 10}, headers=CLIENTE)
    assert r.status_code == 422 and "juan.perez" not in r.text


def test_cuerpo_demasiado_grande_413(api):
    r = api.post("/v1/criterios", content=b"{" + b" " * 70000 + b"}", headers={**CLIENTE, "Content-Type": "application/json"})
    assert r.status_code == 413


def test_guardrail_bloquea_historia_envenenada(api):
    r = api.post("/v1/criterios", json={"historia": HU99}, headers=CLIENTE)
    assert r.status_code == 422 and r.json()["detail"]["error"] == "historia_bloqueada"


def test_pii_se_enmascara_antes_del_modelo(api):
    h = historia_unica("\nContacto: juan.perez@gmail.com, tel 55 1234 5678, CURP GOMC800101HDFRRL09, "
                       "tarjeta 4111 1111 1111 1111")
    cuerpo = api.post("/v1/criterios", json={"historia": h}, headers=CLIENTE).json()
    assert cuerpo["pii_enmascarada"]["entrada"] == {"correo": 1, "telefono": 1, "curp": 1, "tarjeta": 1}


def test_detector_pii_no_marca_datos_de_negocio():
    texto = ("EMP-0001 ana@empresa.com ingresó 2026-01-15; vacaciones del 2026-12-21 al 2026-12-31: 8 días. "
             "Solo 2026 y 2027. Responde 400 con detail.")
    assert enmascarar(texto).hallazgos == {}
    assert enmascarar("token sk-ant-PRUEBA-no-es-real").hallazgos == {"llave_api": 1}


def test_auditoria_registra_acciones_sin_texto_de_historia(api):
    api.post("/v1/criterios", json={"historia": HU99}, headers=CLIENTE)
    log = (Path(config().dir_datos) / "auditoria_api.jsonl").read_text(encoding="utf-8")
    assert "historia_bloqueada" in log and "acceso_denegado" in log
    assert "secretos_demo" not in log and "llave-cliente-prueba" not in log


# --- Observabilidad -------------------------------------------------------------------------
def test_correlation_id_entrante_se_respeta(api):
    r = api.get("/health", headers={"X-Request-ID": "prueba-1234567"})
    assert r.headers["X-Request-ID"] == "prueba-1234567"


def test_metricas_prometheus_y_json(api):
    api.post("/v1/criterios", json={"historia": historia_unica()}, headers=CLIENTE)
    texto = api.get("/metrics", headers=LECTOR).text
    for serie in ("fabrica_peticiones_total", "fabrica_latencia_ms_bucket", "fabrica_costo_usd_total",
                  "fabrica_llamadas_llm_total", "fabrica_cache_total"):
        assert serie in texto
    m = api.get("/v1/metricas", headers=LECTOR).json()
    assert m["rutas"]["/v1/criterios"]["total"] >= 1 and "p95" in m["rutas"]["/v1/criterios"]["latencia_ms"]


# --- Concurrencia ---------------------------------------------------------------------------
def test_peticiones_concurrentes(api):
    with ThreadPoolExecutor(max_workers=10) as pool:
        respuestas = list(pool.map(lambda _: api.post("/v1/criterios", json={"historia": historia_unica()},
                                                      headers=CLIENTE), range(10)))
    assert all(r.status_code == 200 for r in respuestas)
    assert len({r.headers["X-Request-ID"] for r in respuestas}) == 10
