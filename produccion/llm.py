"""Puerta única al modelo en producción: salida estructurada + uso, costo, latencia y traza.

Cada llamada:
- usa el Claude Agent SDK con el token de la cuenta (sin herramientas: `tools=[]`, mínimo privilegio),
- valida la respuesta con Pydantic (el código decide, no el modelo) y reintenta con el error si no cumple,
- devuelve un `Uso` con tokens, costo en USD (precio de lista que reporta el SDK) y latencia,
- queda como run `llm` en LangSmith con `usage_metadata` (tokens y costo), colgado del nodo que la hizo.

Con LLM_FALSO=1 responde de forma determinista sin red (pruebas y CI sin credenciales).
"""
import asyncio
import json
import re
import time
from dataclasses import asdict, dataclass
from typing import Callable, TypeVar

from langsmith import get_current_run_tree, traceable
from pydantic import BaseModel, ValidationError

from produccion.config import config

M = TypeVar("M", bound=BaseModel)


@dataclass
class Uso:
    agente: str
    modelo: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    costo_usd: float = 0.0
    latencia_ms: int = 0
    intentos: int = 1

    def dict(self) -> dict:
        return asdict(self)


class ErrorLLM(RuntimeError):
    """El modelo no respondió con el esquema tras los reintentos, o el SDK falló."""


def _json_de(texto: str) -> str:
    m = re.search(r"\{.*\}", texto or "", flags=re.DOTALL)
    return m.group(0) if m else (texto or "")


async def _consultar(prompt: str, sistema: str, esquema: dict, modelo: str):
    from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

    from agentes.modelo import entorno_cuenta

    opciones = ClaudeAgentOptions(
        model=modelo,
        system_prompt=sistema,
        tools=[],                       # mínimo privilegio: el agente solo razona, no toca archivos ni terminal
        setting_sources=[],             # no hereda CLAUDE.md ni configuración local
        output_format={"type": "json_schema", "schema": esquema},
        max_turns=3,
        env=entorno_cuenta(),
    )
    resultado = None
    async for mensaje in query(prompt=prompt, options=opciones):
        if isinstance(mensaje, ResultMessage):
            resultado = mensaje
    if resultado is None or resultado.is_error:
        raise ErrorLLM(f"El SDK terminó sin resultado válido ({getattr(resultado, 'subtype', 'sin resultado')})")
    return resultado


def _registrar_en_traza(uso: Uso) -> None:
    """Tokens y costo en el run actual de LangSmith: así el proyecto grafica costo por agente y modelo."""
    rt = get_current_run_tree()
    if rt is None:
        return
    rt.metadata.update({
        "ls_provider": "anthropic", "ls_model_name": uso.modelo, "agente": uso.agente, "intentos": uso.intentos,
        "usage_metadata": {"input_tokens": uso.input_tokens, "output_tokens": uso.output_tokens,
                           "total_tokens": uso.input_tokens + uso.output_tokens,
                           "total_cost": round(uso.costo_usd, 6),
                           "input_token_details": {"cache_read": uso.cache_read_tokens,
                                                   "cache_creation": uso.cache_write_tokens}}})


def _entradas(inputs: dict) -> dict:
    """Qué ve LangSmith de la llamada: el prompt (ya sin PII) y el modelo; nunca credenciales."""
    return {"agente": inputs.get("agente"), "modelo": inputs.get("modelo"),
            "sistema": (inputs.get("sistema") or "")[:400], "prompt": inputs.get("prompt")}


def _salidas(resultado) -> dict:
    objeto, uso = resultado
    return {"output": objeto.model_dump(), "uso": uso.dict()}


def llamar(agente: str, prompt: str, esquema: type[M], modelo: str, sistema: str,
           falso: Callable[[], dict] | None = None) -> tuple[M, Uso]:
    """Llamada estructurada con reintentos, medición y traza. Devuelve (objeto validado, uso).
    En LangSmith aparece como `llm:<agente>` con etiquetas del agente y del modelo."""
    return _llamar(agente, prompt, esquema, modelo, sistema, falso,
                   langsmith_extra={"name": f"llm:{agente}", "tags": [f"agente:{agente}", f"modelo:{modelo}"]})


@traceable(run_type="llm", process_inputs=_entradas, process_outputs=_salidas)
def _llamar(agente: str, prompt: str, esquema: type[M], modelo: str, sistema: str,
            falso: Callable[[], dict] | None = None) -> tuple[M, Uso]:
    cfg = config()
    uso = Uso(agente=agente, modelo=modelo)
    inicio = time.perf_counter()
    if cfg.llm_falso:
        datos = falso() if falso else {}
        objeto = esquema.model_validate(datos)
        uso.input_tokens, uso.output_tokens = len(prompt) // 4, len(json.dumps(datos)) // 4
        uso.latencia_ms = int((time.perf_counter() - inicio) * 1000)
        _registrar_en_traza(uso)
        return objeto, uso

    error = ""
    for intento in range(1, cfg.max_reintentos_llm + 1):
        uso.intentos = intento
        texto = prompt + (f"\n\nTu respuesta anterior no cumplió el esquema: {error}" if error else "")
        try:
            r = asyncio.run(_consultar(texto, sistema, esquema.model_json_schema(), modelo))
        except ErrorLLM as e:
            error = str(e)
            continue
        u = r.usage or {}
        uso.input_tokens += (int(u.get("input_tokens", 0)) + int(u.get("cache_creation_input_tokens", 0))
                             + int(u.get("cache_read_input_tokens", 0)))
        uso.output_tokens += int(u.get("output_tokens", 0))
        uso.cache_read_tokens += int(u.get("cache_read_input_tokens", 0))
        uso.cache_write_tokens += int(u.get("cache_creation_input_tokens", 0))
        uso.costo_usd += float(r.total_cost_usd or 0.0)
        try:
            objeto = (esquema.model_validate(r.structured_output) if r.structured_output is not None
                      else esquema.model_validate_json(_json_de(r.result)))
            uso.latencia_ms = int((time.perf_counter() - inicio) * 1000)
            _registrar_en_traza(uso)
            return objeto, uso
        except (ValidationError, json.JSONDecodeError) as e:
            error = str(e)[:400]
    raise ErrorLLM(f"{agente}: el modelo {modelo} no respondió con {esquema.__name__} tras "
                   f"{cfg.max_reintentos_llm} intentos: {error}")
