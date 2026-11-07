"""Sesión 1 · La base de los agentes 1 y 2: herramientas de archivos y el bucle.

Un agente = modelo + instrucciones + herramientas + bucle. Los agentes 1 y 2
usan este mismo bucle; solo cambian sus instrucciones y sus herramientas.
"""
import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from dotenv import load_dotenv

load_dotenv()
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # acentos y flechas en la consola de Windows
RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "salida"
APP = RAIZ / "app"


def rel(ruta: Path) -> str:
    """Ruta relativa a la raíz del repositorio, como la ven los agentes."""
    return str(ruta.resolve().relative_to(RAIZ))


def hu_de(historia: Path) -> str:
    """'historias/HU-01-registrar-empleado.md' -> 'HU-01'."""
    return "-".join(historia.stem.split("-")[:2])


# --- Herramientas ------------------------------------------------------
@dataclass
class Herramienta:
    nombre: str
    descripcion: str
    parametros: dict  # propiedades JSON Schema; todas obligatorias
    funcion: Callable[..., str]

    def esquema(self) -> dict:
        return {"name": self.nombre, "description": self.descripcion,
                "input_schema": {"type": "object", "properties": self.parametros,
                                 "required": list(self.parametros)}}


def _dentro_de(ruta: str, bases: list[Path]) -> Path:
    """Resuelve la ruta y rechaza cualquier cosa fuera de las carpetas permitidas."""
    destino = (RAIZ / ruta).resolve()
    if not any(destino.is_relative_to(b.resolve()) for b in bases):
        permitidas = ", ".join(rel(b) + "/" for b in bases)
        raise PermissionError(f"Ruta no permitida: {ruta}. Solo: {permitidas}")
    return destino


def herramientas_archivos(lectura: list[Path], escritura: Path) -> list[Herramienta]:
    """Herramientas de archivos con permisos mínimos: leer en `lectura`, escribir solo en `escritura`."""
    def leer_archivo(ruta: str) -> str:
        return _dentro_de(ruta, lectura + [escritura]).read_text(encoding="utf-8")

    def listar_archivos(carpeta: str) -> str:
        base = _dentro_de(carpeta, lectura + [escritura])
        return "\n".join(rel(p) for p in sorted(base.rglob("*")) if p.is_file()) or "(vacía)"

    def escribir_archivo(ruta: str, contenido: str) -> str:
        destino = _dentro_de(ruta, [escritura])
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(contenido, encoding="utf-8")
        return f"Escrito {ruta} ({len(contenido)} caracteres)"

    texto = {"type": "string"}
    return [
        Herramienta("leer_archivo", "Lee un archivo de texto. Ejemplo: ruta='historias/HU-01-registrar-empleado.md'.",
                    {"ruta": texto}, leer_archivo),
        Herramienta("listar_archivos", "Lista los archivos de una carpeta. Ejemplo: carpeta='contexto'.",
                    {"carpeta": texto}, listar_archivos),
        Herramienta("escribir_archivo", ("Crea o reemplaza un archivo con el contenido completo. "
                                         f"Solo se permite dentro de {rel(escritura)}/."),
                    {"ruta": texto, "contenido": texto}, escribir_archivo),
    ]


# --- El bucle del agente -------------------------------------------------
def ejecutar_agente(sistema: str, herramientas: list[Herramienta], tarea: str,
                    max_pasos: int = 10, nombre: str = "agente") -> str:
    """Llama al modelo, ejecuta las herramientas que pida y repite hasta que responda sin pedir más.

    Versión con la cuenta personal: el bucle ReAct (modelo -> tool_use -> tool_result -> modelo)
    lo corre el Claude Agent SDK; nuestras herramientas se publican como un servidor MCP en
    proceso y son las ÚNICAS que el agente puede usar (tools=[] apaga Read, Write y Bash).
    max_turns cumple el papel de max_pasos y los errores de herramienta regresan al modelo como texto.
    """
    from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, HookMatcher, ResultMessage, ToolUseBlock,
                                  create_sdk_mcp_server, query, tool)
    from agentes.modelo import entorno_cuenta, modelo
    from seguridad.hooks import auditar

    def envolver(h: Herramienta):
        @tool(h.nombre, h.descripcion, h.esquema()["input_schema"])
        async def ejecutar(args: dict) -> dict:
            try:
                return {"content": [{"type": "text", "text": h.funcion(**args)}]}
            except Exception as e:  # el error regresa al modelo como texto para que se corrija
                return {"content": [{"type": "text", "text": f"Error: {e}"}], "is_error": True}
        return ejecutar

    servidor = create_sdk_mcp_server("fabrica", tools=[envolver(h) for h in herramientas])
    opciones = ClaudeAgentOptions(
        model=modelo(), system_prompt=sistema, cwd=str(RAIZ),
        tools=[], setting_sources=[],
        mcp_servers={"fabrica": servidor},
        allowed_tools=[f"mcp__fabrica__{h.nombre}" for h in herramientas],
        disallowed_tools=["WebFetch", "WebSearch", "Bash", "Read", "Write", "Edit"],
        hooks={"PreToolUse": [HookMatcher(hooks=[auditar(nombre)])]},
        max_turns=max_pasos, env=entorno_cuenta())

    async def correr():
        resultado = None
        async for m in query(prompt=tarea, options=opciones):
            if isinstance(m, AssistantMessage):
                for b in m.content:
                    if isinstance(b, ToolUseBlock):
                        print(f"  [{nombre}] {b.name.split('__')[-1]}({', '.join(b.input)})")
            elif isinstance(m, ResultMessage):
                resultado = m
        return resultado

    r = asyncio.run(correr())
    if r is None:
        raise RuntimeError(f"{nombre}: el modelo terminó sin resultado")
    print(f"  [{nombre}] stop_reason={r.stop_reason} · turnos={r.num_turns}")   # ← diagnóstico
    if r.subtype == "error_max_turns":
        raise RuntimeError(f"{nombre}: se alcanzó el límite de {max_pasos} pasos")
    if r.is_error:
        raise RuntimeError(f"{nombre}: {r.subtype} · {r.result}")
    return r.result or ""
