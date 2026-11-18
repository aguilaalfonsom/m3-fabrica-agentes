"""Caché de resultados (optimización de costos): la misma historia con la misma configuración no vuelve
a llamar al modelo. SQLite en el volumen de datos: sobrevive reinicios y no agrega servicios.

La clave es el hash de (historia normalizada + versión de prompts + modelos): si cambia un prompt o el
ruteo, la clave cambia y no se sirve una respuesta vieja (trade-off: se invalida todo al cambiar prompts).
"""
import hashlib
import json
import re
import sqlite3
import threading
import time

from produccion.config import config

VERSION_PROMPTS = "m4-v1"
_bloqueo = threading.Lock()


def _conexion() -> sqlite3.Connection:
    ruta = config().dir_datos / "cache.sqlite"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(ruta, timeout=10)
    con.execute("CREATE TABLE IF NOT EXISTS cache (clave TEXT PRIMARY KEY, valor TEXT, creado REAL, costo REAL)")
    return con


def clave(historia: str) -> str:
    cfg = config()
    normal = re.sub(r"\s+", " ", historia).strip().lower()
    base = json.dumps([normal, VERSION_PROMPTS, cfg.modelo_clasificador, cfg.modelo_analista,
                       cfg.modelo_disenador, cfg.ruteo_activo, cfg.contexto_recortado])
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def leer(k: str) -> dict | None:
    if not config().cache_activo:
        return None
    with _bloqueo, _conexion() as con:
        fila = con.execute("SELECT valor, creado, costo FROM cache WHERE clave = ?", (k,)).fetchone()
    if not fila or time.time() - fila[1] > config().cache_ttl_s:
        return None
    valor = json.loads(fila[0])
    valor["_costo_original_usd"] = fila[2]
    return valor


def guardar(k: str, valor: dict, costo: float) -> None:
    if not config().cache_activo:
        return
    with _bloqueo, _conexion() as con:
        con.execute("INSERT OR REPLACE INTO cache VALUES (?, ?, ?, ?)", (k, json.dumps(valor), time.time(), costo))
