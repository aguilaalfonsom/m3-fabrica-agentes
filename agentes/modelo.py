"""Acceso al modelo con la cuenta personal de Claude (sin clave de API).

El curso usaba ANTHROPIC_API_KEY con los SDK de Anthropic y LangChain. Esta fábrica habla con
el modelo a través del Claude Agent SDK, que se autentica con el token de la cuenta personal
(`claude setup-token` -> CLAUDE_CODE_OAUTH_TOKEN en .env). El flujo, los contratos y las
validaciones son los mismos; solo cambia la puerta de entrada al modelo.
"""
import asyncio
import json
import os
import re
from typing import TypeVar

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

load_dotenv()
M = TypeVar("M", bound=BaseModel)


def modelo() -> str:
    """Identificador del modelo; se lee de MODEL en .env (nunca fijo en el código)."""
    return os.environ.get("MODEL", "sonnet")


def entorno_cuenta() -> dict[str, str]:
    """Variables que se pasan a Claude Code: el token personal y nunca una clave de API."""
    entorno = {"CLAUDE_CODE_OAUTH_TOKEN": os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "")}
    if not entorno["CLAUDE_CODE_OAUTH_TOKEN"]:
        entorno.pop("CLAUDE_CODE_OAUTH_TOKEN")
    return entorno


async def _consultar(prompt: str, opciones: ClaudeAgentOptions) -> ResultMessage:
    resultado = None
    async for mensaje in query(prompt=prompt, options=opciones):
        if isinstance(mensaje, ResultMessage):
            resultado = mensaje
    if resultado is None:
        raise RuntimeError("El modelo terminó sin resultado")
    return resultado


def _json_de(texto: str) -> str:
    """Extrae el primer objeto JSON de una respuesta de texto (por si llega entre ```json)."""
    m = re.search(r"\{.*\}", texto or "", flags=re.DOTALL)
    return m.group(0) if m else (texto or "")


def estructurado(prompt: str, esquema: type[M], sistema: str = "", max_intentos: int = 2) -> M:
    """Equivalente a `with_structured_output(esquema).invoke(prompt)`: el modelo responde
    con el esquema Pydantic y el código lo valida. Sin herramientas: solo razona y responde."""
    opciones = ClaudeAgentOptions(
        model=modelo(),
        system_prompt=sistema or "Respondes únicamente con el objeto JSON que se te pide.",
        tools=[],                                   # sin Read, Write ni Bash: solo texto
        setting_sources=[],                         # no carga CLAUDE.md ni configuración local
        output_format={"type": "json_schema", "schema": esquema.model_json_schema()},
        max_turns=3,
        env=entorno_cuenta(),
    )
    error = ""
    for _ in range(max_intentos):
        r = asyncio.run(_consultar(prompt + (f"\n\nTu respuesta anterior no era válida: {error}" if error else ""),
                                   opciones))
        try:
            if r.structured_output is not None:
                return esquema.model_validate(r.structured_output)
            return esquema.model_validate_json(_json_de(r.result))
        except (ValidationError, json.JSONDecodeError) as e:   # el validador decide, no el modelo
            error = str(e)[:500]
    raise ValueError(f"El modelo no respondió con el esquema {esquema.__name__}: {error}")
