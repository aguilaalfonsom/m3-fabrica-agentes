"""Configuración de producción: todo sale de variables de entorno (12-factor), nada fijo en el código.

Los secretos (token de Claude, LangSmith, API keys de clientes) solo se leen aquí y nunca se registran:
`Config.publica()` devuelve la configuración sin secretos para /ready y para los logs de arranque.
"""
import hashlib
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")


def _bool(nombre: str, defecto: bool) -> bool:
    return os.environ.get(nombre, str(defecto)).strip().lower() in ("1", "true", "si", "sí", "yes")


def _hash(llave: str) -> str:
    return hashlib.sha256(llave.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Config:
    # --- modelos (ruteo) ---------------------------------------------------------------
    modelo_clasificador: str = field(default_factory=lambda: os.environ.get("MODELO_CLASIFICADOR", "claude-haiku-5-5"))
    modelo_analista: str = field(default_factory=lambda: os.environ.get("MODELO_ANALISTA", "claude-sonnet-5-5"))
    modelo_disenador: str = field(default_factory=lambda: os.environ.get("MODELO_DISENADOR", "claude-haiku-5-5"))
    modelo_respaldo: str = field(default_factory=lambda: os.environ.get("MODELO_RESPALDO", "claude-sonnet-5-5"))
    # --- estrategias de costo (se apagan para medir el baseline) -----------------------
    cache_activo: bool = field(default_factory=lambda: _bool("CACHE_ACTIVO", True))
    ruteo_activo: bool = field(default_factory=lambda: _bool("RUTEO_ACTIVO", True))
    contexto_recortado: bool = field(default_factory=lambda: _bool("CONTEXTO_RECORTADO", True))
    cache_ttl_s: int = field(default_factory=lambda: int(os.environ.get("CACHE_TTL_S", "86400")))
    # --- capacidad y resiliencia -------------------------------------------------------
    max_concurrencia: int = field(default_factory=lambda: int(os.environ.get("MAX_CONCURRENCIA", "4")))
    max_en_cola: int = field(default_factory=lambda: int(os.environ.get("MAX_EN_COLA", "8")))
    timeout_s: float = field(default_factory=lambda: float(os.environ.get("TIMEOUT_S", "240")))
    max_reintentos_llm: int = field(default_factory=lambda: int(os.environ.get("MAX_REINTENTOS_LLM", "2")))
    presupuesto_peticion_usd: float = field(default_factory=lambda: float(os.environ.get("PRESUPUESTO_PETICION_USD", "0.50")))
    # --- seguridad ---------------------------------------------------------------------
    limite_por_minuto: int = field(default_factory=lambda: int(os.environ.get("LIMITE_POR_MINUTO", "30")))
    max_caracteres_historia: int = field(default_factory=lambda: int(os.environ.get("MAX_CARACTERES_HISTORIA", "6000")))
    # --- rutas de datos (escribibles; el resto del contenedor es de solo lectura) --------
    dir_datos: Path = field(default_factory=lambda: Path(os.environ.get("DIR_DATOS", str(RAIZ / "produccion" / "datos"))))
    # --- modo de pruebas: respuestas deterministas sin llamar al modelo (CI) -------------
    llm_falso: bool = field(default_factory=lambda: _bool("LLM_FALSO", False))

    @property
    def llaves(self) -> dict[str, str]:
        """hash sha256 de cada API key -> rol. Formato en .env: API_KEYS=rol:llave,rol:llave.
        En memoria solo quedan los hashes; la llave en claro no se guarda ni se registra."""
        resultado = {}
        for par in os.environ.get("API_KEYS", "").split(","):
            if ":" in par:
                rol, llave = par.split(":", 1)
                if llave.strip():
                    resultado[_hash(llave.strip())] = rol.strip()
        return resultado

    def publica(self) -> dict:
        """Configuración sin secretos (para /ready y los logs de arranque)."""
        return {
            "modelos": {"clasificador": self.modelo_clasificador, "analista": self.modelo_analista,
                        "disenador": self.modelo_disenador, "respaldo": self.modelo_respaldo},
            "estrategias": {"cache": self.cache_activo, "ruteo": self.ruteo_activo,
                            "contexto_recortado": self.contexto_recortado},
            "capacidad": {"max_concurrencia": self.max_concurrencia, "max_en_cola": self.max_en_cola,
                          "timeout_s": self.timeout_s},
            "seguridad": {"limite_por_minuto": self.limite_por_minuto, "roles": sorted(set(self.llaves.values())),
                          "max_caracteres_historia": self.max_caracteres_historia},
            "llm_falso": self.llm_falso,
            "langsmith": bool(os.environ.get("LANGSMITH_API_KEY")) and _bool("LANGSMITH_TRACING", False),
            "credencial_modelo": bool(os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")) or self.llm_falso,
        }


@lru_cache
def config() -> Config:
    return Config()
