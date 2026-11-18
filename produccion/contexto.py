"""Contexto que recibe el analista. Optimización de prompt: solo las secciones que aplican a la historia.

Los archivos de contexto tienen un bloque general (`# Reglas de negocio…`, `# Convenciones…`) y bloques
por historia cuyo título termina en `(HU-xx)`. El baseline manda los dos archivos completos; el modo
recortado manda el bloque general sin las secciones que no le sirven a un analista (arquitectura, puertos,
reglas para quien programa) y solo el bloque de la HU que se está analizando.
"""
import re
from functools import lru_cache

from produccion.config import RAIZ

ARCHIVOS = ("reglas_negocio.md", "convenciones_app.md")
SECCIONES_FUERA = ("Arquitectura", "Puertos", "Reglas para quien programa")


@lru_cache
def _leer(nombre: str) -> str:
    return (RAIZ / "contexto" / nombre).read_text(encoding="utf-8")


def _bloques(texto: str) -> list[str]:
    """Separa por títulos de nivel 1 (`# `), conservando el título en cada bloque."""
    partes = re.split(r"(?m)^(?=# )", texto)
    return [p for p in partes if p.strip()]


def _sin_secciones(bloque: str) -> str:
    secciones = re.split(r"(?m)^(?=## )", bloque)
    return "".join(s for s in secciones if not any(s.startswith(f"## {f}") for f in SECCIONES_FUERA))


def contexto_para(hu: str, recortado: bool) -> str:
    """Texto de contexto para el analista de la historia `hu` (por ejemplo «HU-10»)."""
    if not recortado:
        return "\n\n".join(_leer(n) for n in ARCHIVOS)
    partes = []
    for nombre in ARCHIVOS:
        for bloque in _bloques(_leer(nombre)):
            titulo = bloque.splitlines()[0]
            especifico = re.search(r"\((HU-\d+)\)", titulo)
            if especifico and especifico.group(1) != hu:
                continue                      # bloque de otra historia: no le sirve a esta
            partes.append(_sin_secciones(bloque).strip())
    return "\n\n".join(partes)
