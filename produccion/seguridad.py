"""Controles de seguridad de la API: autenticación por API key con roles, límite de peticiones y auditoría.

- Mínimo privilegio: el rol `cliente` puede generar criterios; el rol `lector` solo ve métricas y el panel.
  `/health` es público (lo usan el balanceador y Docker) y no revela nada.
- Las llaves se comparan por hash sha256 en tiempo constante; en memoria nunca queda la llave en claro.
- Límite por llave con ventana deslizante de 60 s (429 + Retry-After).
- Auditoría: una línea JSON por acción relevante, con huella (hash) del contenido en lugar del contenido.
"""
import hashlib
import hmac
import json
import os
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader

from produccion.config import config
from produccion.observabilidad import id_peticion, metricas

PERMISOS = {"cliente": {"criterios", "metricas"}, "lector": {"metricas"}, "admin": {"criterios", "metricas", "auditoria"}}


def huella(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:16]


def _rol_de(llave: str) -> str | None:
    h = hashlib.sha256(llave.encode("utf-8")).hexdigest()
    for guardado, rol in config().llaves.items():
        if hmac.compare_digest(guardado, h):
            return rol
    return None


class Limitador:
    def __init__(self) -> None:
        self._ventanas: dict[str, deque] = defaultdict(deque)
        self._bloqueo = threading.Lock()

    def permitir(self, clave: str, limite: int) -> tuple[bool, int]:
        ahora = time.time()
        with self._bloqueo:
            v = self._ventanas[clave]
            while v and ahora - v[0] > 60:
                v.popleft()
            if len(v) >= limite:
                return False, int(60 - (ahora - v[0])) + 1
            v.append(ahora)
            return True, 0


limitador = Limitador()


esquema_llave = APIKeyHeader(name="X-API-Key", auto_error=False,
                             description="API key del cliente. Roles: cliente (criterios + métricas), lector (métricas).")


def requiere(permiso: str):
    """Dependencia de FastAPI: valida la API key, el permiso del rol y el límite de peticiones."""
    def dependencia(request: Request, x_api_key: str | None = Security(esquema_llave)) -> str:
        if not x_api_key:
            metricas.contar("bloqueos", "sin_llave")
            auditar("acceso_denegado", motivo="sin_llave", ruta=request.url.path)
            raise HTTPException(401, "Falta el encabezado X-API-Key", headers={"WWW-Authenticate": "ApiKey"})
        rol = _rol_de(x_api_key)
        if rol is None:
            metricas.contar("bloqueos", "llave_invalida")
            auditar("acceso_denegado", motivo="llave_invalida", ruta=request.url.path)
            raise HTTPException(401, "API key inválida", headers={"WWW-Authenticate": "ApiKey"})
        if permiso not in PERMISOS.get(rol, set()):
            metricas.contar("bloqueos", "sin_permiso")
            auditar("acceso_denegado", motivo="sin_permiso", rol=rol, ruta=request.url.path)
            raise HTTPException(403, f"El rol «{rol}» no tiene permiso para esta operación")
        ok, espera = limitador.permitir(huella(x_api_key), config().limite_por_minuto)
        if not ok:
            metricas.contar("bloqueos", "limite_peticiones")
            auditar("limite_excedido", rol=rol, ruta=request.url.path)
            raise HTTPException(429, "Demasiadas peticiones para esta API key", headers={"Retry-After": str(espera)})
        request.state.rol = rol
        request.state.cliente = huella(x_api_key)
        return rol
    return dependencia


_bloqueo_auditoria = threading.Lock()


def auditar(accion: str, **datos) -> None:
    """Registro de auditoría append-only (JSONL). Nunca guarda texto de historias ni credenciales."""
    registro = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z", "request_id": id_peticion.get(),
                "accion": accion, **datos}
    ruta = config().dir_datos / "auditoria_api.jsonl"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with _bloqueo_auditoria, open(ruta, "a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    if os.environ.get("AUDITORIA_STDOUT", "0") == "1":
        print(json.dumps({"auditoria": registro}, ensure_ascii=False))
