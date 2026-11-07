"""Sesión 4 · Triage: ante pruebas fallidas, decide qué agente debe corregir.

Es el supervisor del flujo E2E: no corrige nada, solo enruta con una justificación.
"""
from typing import Literal

from pydantic import BaseModel

from agentes.base import SALIDA
from agentes.modelo import estructurado


class Diagnostico(BaseModel):
    responsable: Literal["desarrollador", "automatizador", "despliegue", "persona"]
    causa: str          # qué falló, en una o dos frases
    criterio: str       # escenario de aceptación que se usa como referencia
    instruccion: str    # qué debe corregir el responsable


PROMPT = """Eres líder técnico. Unas pruebas automatizadas fallaron. Decide quién debe corregir:
- "desarrollador": la aplicación no cumple un criterio de aceptación.
- "automatizador": la prueba contradice el criterio, usa un selector incorrecto o es frágil.
- "despliegue": la aplicación no responde (conexión rechazada, 502, contenedor caído).
- "persona": falla el entorno de la máquina y ningún agente lo puede arreglar con sus permisos
  (por ejemplo, falta el navegador de Playwright, un programa no está instalado o no hay red).
  Ningún agente debe gastar un ciclo en esto: se escala de inmediato.
El criterio de aceptación manda: si la prueba y la aplicación no coinciden, gana quien siga el criterio.

## Criterios de aceptación
{criterios}

## Pruebas fallidas
{fallos}"""


def diagnosticar(hu: str, fallos: str) -> Diagnostico:
    criterios = (SALIDA / hu / "criterios.feature").read_text(encoding="utf-8")
    return estructurado(PROMPT.format(criterios=criterios, fallos=fallos[:6000]), Diagnostico,
                        sistema="Eres el agente de triage: enrutas fallos, no corriges código.")
