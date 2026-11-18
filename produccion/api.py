"""API REST de la fábrica de agentes en producción.

Ejecutar:  python -m uvicorn produccion.api:app --host 0.0.0.0 --port 8000
Docs:      /docs (Swagger UI) · /redoc · /openapi.json
"""
import asyncio
import json
import logging
import re
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import anyio
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field, field_validator

from produccion import cache
from produccion.config import config
from produccion.grafo import grafo
from produccion.llm import ErrorLLM
from produccion.observabilidad import configurar_logs, id_peticion, log, metricas
from produccion.seguridad import auditar, huella, requiere

VERSION = "1.0.0"
logger = configurar_logs()
_semaforo: asyncio.Semaphore | None = None
_esperando = 0


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    global _semaforo
    cfg = config()
    _semaforo = asyncio.Semaphore(cfg.max_concurrencia)
    cfg.dir_datos.mkdir(parents=True, exist_ok=True)
    log(logging.INFO, "API iniciada", version=VERSION, config=cfg.publica())
    auditar("api_iniciada", version=VERSION)
    yield
    auditar("api_detenida")


DESCRIPCION = """
Fábrica de agentes (Módulo 3) llevada a producción. Recibe una **historia de usuario** y una cadena de
agentes LangGraph devuelve **criterios de aceptación en Gherkin** y **casos de prueba**:

`preparar (PII)` → `filtrar (guardrail, Haiku)` → `analizar (Sonnet)` ⇄ `validar_criterios` →
`disenar (Haiku → Sonnet en cascada)` ⇄ `validar_casos` → `validar_salida (PII)`

* **Autenticación**: encabezado `X-API-Key` (botón *Authorize*). Roles: `cliente`, `lector`.
* **Trazabilidad**: cada respuesta trae `X-Request-ID`; el mismo id aparece en logs, auditoría y LangSmith.
* **Costos**: cada respuesta reporta tokens, costo por agente y si vino de caché.
"""

app = FastAPI(title="Fábrica de agentes · API de producción", version=VERSION, description=DESCRIPCION,
              lifespan=ciclo_de_vida,
              openapi_tags=[{"name": "operación", "description": "Salud y disponibilidad"},
                            {"name": "agentes", "description": "Cadena multi-agente"},
                            {"name": "observabilidad", "description": "Métricas y panel"}])


# --- Middleware: correlation ID, métricas, logs y encabezados de seguridad ---------------
_ID_VALIDO = re.compile(r"^[A-Za-z0-9\-]{8,64}$")
MAX_BYTES = 64 * 1024


@app.exception_handler(RequestValidationError)
async def validacion_sin_eco(request: Request, error: RequestValidationError):
    """422 sin devolver el texto recibido (`input`): un error nunca debe reflejar PII ni secretos."""
    detalle = [{"campo": ".".join(str(p) for p in e["loc"][1:]), "error": e["msg"]} for e in error.errors()]
    auditar("entrada_invalida", errores=[d["error"][:120] for d in detalle])
    metricas.contar("bloqueos", "entrada_invalida")
    return JSONResponse({"detail": detalle}, status_code=422)


@app.middleware("http")
async def middleware(request: Request, siguiente):
    entrante = request.headers.get("X-Request-ID", "")
    rid = entrante if _ID_VALIDO.match(entrante) else uuid.uuid4().hex
    token = id_peticion.set(rid)
    inicio = time.perf_counter()
    ruta = request.scope.get("route").path if request.scope.get("route") else request.url.path
    try:
        if int(request.headers.get("content-length") or 0) > MAX_BYTES:
            respuesta = JSONResponse({"detail": "Cuerpo demasiado grande"}, status_code=413)
        else:
            respuesta = await siguiente(request)
    except Exception:                                    # nunca se filtra un stack trace al cliente
        logger.exception("Error no controlado")
        respuesta = JSONResponse({"detail": "Error interno", "request_id": rid}, status_code=500)
    ms = (time.perf_counter() - inicio) * 1000
    ruta = request.scope.get("route").path if request.scope.get("route") else ruta
    if not ruta.startswith(("/docs", "/openapi", "/redoc", "/favicon")):
        metricas.peticion(ruta, respuesta.status_code, ms)
        log(logging.INFO, "petición", metodo=request.method, ruta=ruta, estado=respuesta.status_code,
            latencia_ms=round(ms, 1), cliente=getattr(request.state, "cliente", None))
    respuesta.headers["X-Request-ID"] = rid
    respuesta.headers["X-Content-Type-Options"] = "nosniff"
    respuesta.headers["X-Frame-Options"] = "DENY"
    respuesta.headers["Referrer-Policy"] = "no-referrer"
    respuesta.headers["Cache-Control"] = "no-store"
    id_peticion.reset(token)
    return respuesta


# --- Contratos ---------------------------------------------------------------------------
class SolicitudCriterios(BaseModel):
    historia: str = Field(..., min_length=30, description="Historia de usuario en Markdown (Como…, quiero…, para…)",
                          examples=["# HU-02 · Consultar el directorio de empleados\n\nComo persona del área de "
                                    "Recursos Humanos,\nquiero ver el directorio de empleados, buscarlos por nombre o "
                                    "correo y filtrarlos por departamento,\npara encontrar rápido a una persona."])

    @field_validator("historia")
    @classmethod
    def validar_historia(cls, v: str) -> str:
        if len(v) > config().max_caracteres_historia:
            raise ValueError(f"La historia excede {config().max_caracteres_historia} caracteres")
        if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", v):
            raise ValueError("La historia contiene caracteres de control")
        if not re.search(r"\b(como|quiero|para)\b", v, flags=re.IGNORECASE):
            raise ValueError("No parece una historia de usuario (falta «Como…, quiero…, para…»)")
        return v


class UsoAgente(BaseModel):
    agente: str
    modelo: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    costo_usd: float
    latencia_ms: int
    intentos: int


class RespuestaCriterios(BaseModel):
    request_id: str
    hu: str
    gherkin: str
    preguntas_abiertas: list[str]
    casos: list[dict]
    pii_enmascarada: dict = Field(description="Cantidad de datos sensibles enmascarados por tipo (entrada/salida)")
    desde_cache: bool
    costo_usd: float
    latencia_ms: int
    agentes: list[UsoAgente]


# --- Endpoints -----------------------------------------------------------------------------
@app.get("/health", tags=["operación"], summary="Liveness: el proceso responde")
def health():
    return {"estado": "ok", "version": VERSION}


@app.get("/ready", tags=["operación"], summary="Readiness: dependencias y configuración listas")
def ready():
    cfg = config()
    publica = cfg.publica()
    checks = {"credencial_modelo": publica["credencial_modelo"], "datos_escribibles": _escribible(cfg.dir_datos),
              "grafo_compilado": grafo is not None, "llaves_configuradas": bool(cfg.llaves)}
    cuerpo = {"listo": all(checks.values()), "checks": checks, "langsmith": publica["langsmith"],
              "estrategias": publica["estrategias"], "modelos": publica["modelos"], "capacidad": publica["capacidad"]}
    return JSONResponse(cuerpo, status_code=200 if cuerpo["listo"] else 503)


def _escribible(ruta: Path) -> bool:
    try:
        ruta.mkdir(parents=True, exist_ok=True)
        prueba = ruta / ".prueba"
        prueba.write_text("ok")
        prueba.unlink()
        return True
    except OSError:
        return False


@app.post("/v1/criterios", tags=["agentes"], response_model=RespuestaCriterios,
          summary="Historia de usuario → criterios Gherkin y casos de prueba",
          responses={401: {"description": "Sin API key o inválida"}, 403: {"description": "Rol sin permiso"},
                     422: {"description": "Entrada inválida o historia bloqueada por el guardrail"},
                     429: {"description": "Límite por llave o capacidad llena (ver Retry-After)"},
                     502: {"description": "Los agentes no lograron una salida válida"},
                     504: {"description": "Tiempo máximo excedido"}})
async def criterios(solicitud: SolicitudCriterios, request: Request, rol: str = Depends(requiere("criterios"))):
    global _esperando
    cfg = config()
    rid = id_peticion.get()
    inicio = time.perf_counter()
    k = cache.clave(solicitud.historia)
    auditar("criterios_solicitados", rol=rol, cliente=request.state.cliente, huella_historia=huella(solicitud.historia),
            caracteres=len(solicitud.historia))

    guardado = cache.leer(k)
    if guardado:
        metricas.contar("cache", "acierto")
        metricas.ahorro_cache_usd += guardado.pop("_costo_original_usd", 0.0)
        auditar("criterios_desde_cache", cliente=request.state.cliente, huella_historia=huella(solicitud.historia))
        return {**guardado, "request_id": rid, "desde_cache": True, "costo_usd": 0.0,
                "latencia_ms": int((time.perf_counter() - inicio) * 1000), "agentes": []}
    metricas.contar("cache", "fallo")

    # control de capacidad: tope de ejecuciones simultáneas + cola acotada (backpressure)
    if _semaforo.locked() and _esperando >= cfg.max_en_cola:
        metricas.contar("bloqueos", "capacidad")
        raise HTTPException(429, "Capacidad llena, intenta más tarde", headers={"Retry-After": "30"})
    _esperando += 1
    try:
        await _semaforo.acquire()
    finally:
        _esperando -= 1
    metricas.en_curso += 1
    try:
        estado = await asyncio.wait_for(anyio.to_thread.run_sync(_ejecutar, solicitud.historia, rid,
                                                                 request.state.cliente), cfg.timeout_s)
    except asyncio.TimeoutError:
        auditar("criterios_timeout", cliente=request.state.cliente)
        raise HTTPException(504, f"Los agentes excedieron {cfg.timeout_s:.0f} s")
    except ErrorLLM as e:
        log(logging.ERROR, "fallo del modelo", error=str(e)[:300])
        auditar("criterios_error_llm", cliente=request.state.cliente)
        raise HTTPException(502, "Los agentes no lograron una respuesta válida")
    finally:
        metricas.en_curso -= 1
        _semaforo.release()

    resultado = estado.get("resultado")
    costo = round(estado.get("costo_usd", 0.0), 6)
    pii = {"entrada": estado.get("pii_entrada", {}), "salida": estado.get("pii_salida", {})}
    if pii["entrada"] or pii["salida"]:
        auditar("pii_enmascarada", cliente=request.state.cliente, **pii)
    if resultado == "bloqueada":
        metricas.contar("bloqueos", "guardrail")
        auditar("historia_bloqueada", cliente=request.state.cliente, motivo=estado.get("motivo", "")[:200],
                huella_historia=huella(solicitud.historia), costo_usd=costo)
        raise HTTPException(422, {"error": "historia_bloqueada", "motivo": estado.get("motivo"), "request_id": rid})
    if resultado != "ok":
        auditar("criterios_invalidos", cliente=request.state.cliente, resultado=resultado, costo_usd=costo)
        raise HTTPException(502, {"error": resultado, "problemas": estado.get("problemas", [])[:5]})

    cuerpo = {"hu": estado["hu"], "gherkin": estado["gherkin"], "preguntas_abiertas": estado.get("preguntas", []),
              "casos": estado["plan"]["casos"], "pii_enmascarada": pii}
    cache.guardar(k, cuerpo, costo)
    auditar("criterios_generados", cliente=request.state.cliente, hu=estado["hu"], costo_usd=costo,
            escenarios=estado["gherkin"].count("Escenario:"), casos=len(estado["plan"]["casos"]))
    return {**cuerpo, "request_id": rid, "desde_cache": False, "costo_usd": costo,
            "latencia_ms": int((time.perf_counter() - inicio) * 1000), "agentes": estado.get("usos", [])}


def _ejecutar(historia: str, rid: str, cliente: str) -> dict:
    """Corre el grafo en un hilo del pool. La traza de LangSmith lleva el request_id para correlacionar."""
    token = id_peticion.set(rid)
    try:
        return grafo.invoke({"historia": historia},
                            config={"run_name": "criterios", "tags": ["produccion", f"v{VERSION}"],
                                    "metadata": {"request_id": rid, "cliente": cliente,
                                                 "estrategias": config().publica()["estrategias"]}})
    finally:
        id_peticion.reset(token)


@app.get("/v1/metricas", tags=["observabilidad"], summary="Métricas en JSON (latencia, errores, costo, caché)")
def metricas_json(rol: str = Depends(requiere("metricas"))):
    return metricas.resumen()


@app.get("/metrics", tags=["observabilidad"], response_class=PlainTextResponse,
         summary="Métricas en formato Prometheus")
def metricas_prometheus(rol: str = Depends(requiere("metricas"))):
    return metricas.prometheus()


@app.get("/dashboard", tags=["observabilidad"], response_class=HTMLResponse, summary="Panel de operación")
def dashboard():
    html = (Path(__file__).parent / "dashboard.html").read_text(encoding="utf-8")
    r = HTMLResponse(html)
    r.headers["Content-Security-Policy"] = ("default-src 'self'; script-src 'self' 'unsafe-inline'; "
                                            "style-src 'self' 'unsafe-inline'; connect-src 'self'")
    return r
