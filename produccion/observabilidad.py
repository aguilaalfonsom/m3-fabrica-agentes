"""Observabilidad: logs JSON con correlation ID, métricas (latencia, errores, costo) y formato Prometheus.

- `id_peticion` vive en un ContextVar: cada línea de log de una petición lleva el mismo `request_id`,
  igual que su traza en LangSmith (metadata `request_id`) y su registro de auditoría.
- Los logs pasan por un filtro que enmascara secretos aunque alguien los registre por error.
- Las métricas se guardan en memoria del proceso y se exponen en /metrics (Prometheus) y /v1/metricas (JSON).
"""
import json
import logging
import os
import re
import sys
import threading
import time
from collections import defaultdict, deque
from contextvars import ContextVar

id_peticion: ContextVar[str] = ContextVar("id_peticion", default="-")

_SECRETOS = re.compile(r"(sk-ant-[A-Za-z0-9_\-]{6})[A-Za-z0-9_\-]+|(lsv2_[A-Za-z0-9]{4})[A-Za-z0-9_]+"
                       r"|(Bearer\s+)[A-Za-z0-9._\-]+")


def _tapar(texto: str) -> str:
    return _SECRETOS.sub(lambda m: (m.group(1) or m.group(2) or m.group(3)) + "***", texto)


class FormatoJSON(logging.Formatter):
    def format(self, registro: logging.LogRecord) -> str:
        datos = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(registro.created)) + "Z",
                 "nivel": registro.levelname, "logger": registro.name, "request_id": id_peticion.get(),
                 "mensaje": registro.getMessage()}
        datos.update(getattr(registro, "extra_datos", {}))
        if registro.exc_info:
            datos["error"] = self.formatException(registro.exc_info).splitlines()[-1]
        return _tapar(json.dumps(datos, ensure_ascii=False, default=str))


def configurar_logs() -> logging.Logger:
    raiz = logging.getLogger()
    raiz.handlers.clear()
    manejador = logging.StreamHandler(sys.stdout)
    manejador.setFormatter(FormatoJSON())
    raiz.addHandler(manejador)
    raiz.setLevel(os.environ.get("NIVEL_LOG", "INFO"))
    for ruidoso in ("httpx", "urllib3", "langsmith", "uvicorn.access"):
        logging.getLogger(ruidoso).setLevel(logging.WARNING)
    return logging.getLogger("fabrica")


def log(nivel: int, mensaje: str, **datos) -> None:
    logging.getLogger("fabrica").log(nivel, mensaje, extra={"extra_datos": datos})


# --- Métricas -------------------------------------------------------------------------
CUBETAS_MS = (250, 500, 1000, 2500, 5000, 10000, 20000, 40000, 80000, 160000)


class Metricas:
    """Contadores e histogramas en memoria, seguros entre hilos."""

    def __init__(self) -> None:
        self._bloqueo = threading.Lock()
        self.inicio = time.time()
        self.peticiones = defaultdict(int)            # (ruta, estado) -> n
        self.latencias = defaultdict(lambda: [0] * (len(CUBETAS_MS) + 1))
        self.latencia_suma = defaultdict(float)
        self.recientes = defaultdict(lambda: deque(maxlen=500))   # ruta -> latencias para p50/p95
        self.costo_usd = defaultdict(float)           # modelo -> USD
        self.tokens = defaultdict(int)                # (modelo, tipo) -> n
        self.llamadas_llm = defaultdict(int)          # (agente, modelo) -> n
        self.cache = defaultdict(int)                 # acierto / fallo
        self.bloqueos = defaultdict(int)              # motivo -> n (guardrail, pii, auth, limite...)
        self.pii = defaultdict(int)                   # tipo -> n
        self.en_curso = 0
        self.ahorro_cache_usd = 0.0

    def peticion(self, ruta: str, estado: int, ms: float) -> None:
        with self._bloqueo:
            self.peticiones[(ruta, estado)] += 1
            i = next((n for n, c in enumerate(CUBETAS_MS) if ms <= c), len(CUBETAS_MS))
            self.latencias[ruta][i] += 1
            self.latencia_suma[ruta] += ms
            self.recientes[ruta].append(ms)

    def uso_llm(self, uso) -> None:
        with self._bloqueo:
            self.costo_usd[uso.modelo] += uso.costo_usd
            self.tokens[(uso.modelo, "entrada")] += uso.input_tokens
            self.tokens[(uso.modelo, "salida")] += uso.output_tokens
            self.tokens[(uso.modelo, "cache_lectura")] += uso.cache_read_tokens
            self.llamadas_llm[(uso.agente, uso.modelo)] += 1

    def contar(self, tabla: str, clave: str, n: int = 1) -> None:
        with self._bloqueo:
            getattr(self, tabla)[clave] += n

    def resumen(self) -> dict:
        with self._bloqueo:
            def pct(valores, p):
                v = sorted(valores)
                return round(v[min(len(v) - 1, int(len(v) * p))], 1) if v else 0
            rutas = {}
            for (ruta, estado), n in self.peticiones.items():
                r = rutas.setdefault(ruta, {"total": 0, "errores": 0, "por_estado": {}})
                r["total"] += n
                r["errores"] += n if estado >= 500 else 0
                r["por_estado"][str(estado)] = n
            for ruta, r in rutas.items():
                r["latencia_ms"] = {"p50": pct(self.recientes[ruta], .5), "p95": pct(self.recientes[ruta], .95),
                                    "promedio": round(self.latencia_suma[ruta] / max(r["total"], 1), 1)}
            aciertos, fallos = self.cache["acierto"], self.cache["fallo"]
            return {
                "uptime_s": int(time.time() - self.inicio), "en_curso": self.en_curso, "rutas": rutas,
                "costo_usd": {m: round(c, 6) for m, c in self.costo_usd.items()},
                "costo_total_usd": round(sum(self.costo_usd.values()), 6),
                "ahorro_cache_usd": round(self.ahorro_cache_usd, 6),
                "tokens": {f"{m}|{t}": n for (m, t), n in self.tokens.items()},
                "llamadas_llm": {f"{a}|{m}": n for (a, m), n in self.llamadas_llm.items()},
                "cache": {"aciertos": aciertos, "fallos": fallos,
                          "tasa_aciertos": round(aciertos / (aciertos + fallos), 3) if aciertos + fallos else 0},
                "bloqueos": dict(self.bloqueos), "pii_detectada": dict(self.pii),
            }

    def prometheus(self) -> str:
        """Formato de exposición de Prometheus (texto) sin dependencias."""
        with self._bloqueo:
            l = ["# HELP fabrica_peticiones_total Peticiones HTTP por ruta y estado",
                 "# TYPE fabrica_peticiones_total counter"]
            l += [f'fabrica_peticiones_total{{ruta="{r}",estado="{e}"}} {n}' for (r, e), n in self.peticiones.items()]
            l += ["# HELP fabrica_latencia_ms Latencia de peticiones en milisegundos",
                  "# TYPE fabrica_latencia_ms histogram"]
            for ruta, cubetas in self.latencias.items():
                acumulado = 0
                for c, n in zip(CUBETAS_MS + ("+Inf",), cubetas):
                    acumulado += n
                    l.append(f'fabrica_latencia_ms_bucket{{ruta="{ruta}",le="{c}"}} {acumulado}')
                l.append(f'fabrica_latencia_ms_sum{{ruta="{ruta}"}} {self.latencia_suma[ruta]:.1f}')
                l.append(f'fabrica_latencia_ms_count{{ruta="{ruta}"}} {acumulado}')
            l += ["# HELP fabrica_costo_usd_total Costo de LLM (precio de lista) por modelo",
                  "# TYPE fabrica_costo_usd_total counter"]
            l += [f'fabrica_costo_usd_total{{modelo="{m}"}} {c:.6f}' for m, c in self.costo_usd.items()]
            l += ["# TYPE fabrica_tokens_total counter"]
            l += [f'fabrica_tokens_total{{modelo="{m}",tipo="{t}"}} {n}' for (m, t), n in self.tokens.items()]
            l += ["# TYPE fabrica_llamadas_llm_total counter"]
            l += [f'fabrica_llamadas_llm_total{{agente="{a}",modelo="{m}"}} {n}'
                  for (a, m), n in self.llamadas_llm.items()]
            l += ["# TYPE fabrica_cache_total counter"]
            l += [f'fabrica_cache_total{{resultado="{k}"}} {n}' for k, n in self.cache.items()]
            l += ["# TYPE fabrica_bloqueos_total counter"]
            l += [f'fabrica_bloqueos_total{{motivo="{k}"}} {n}' for k, n in self.bloqueos.items()]
            l += ["# TYPE fabrica_pii_detectada_total counter"]
            l += [f'fabrica_pii_detectada_total{{tipo="{k}"}} {n}' for k, n in self.pii.items()]
            l += ["# TYPE fabrica_peticiones_en_curso gauge", f"fabrica_peticiones_en_curso {self.en_curso}",
                  "# TYPE fabrica_ahorro_cache_usd_total counter",
                  f"fabrica_ahorro_cache_usd_total {self.ahorro_cache_usd:.6f}"]
            return "\n".join(l) + "\n"


metricas = Metricas()
