"""Detección y enmascarado de PII y secretos en prompts y respuestas (sin dependencias externas).

Se aplica dos veces: a la historia ANTES de que llegue a cualquier modelo (lo que sale de la empresa ya va
enmascarado) y a la respuesta ANTES de devolverla (por si el modelo inventó o copió datos sensibles).
Los detectores son deterministas y auditables; los de tarjeta y CURP validan estructura para bajar los
falsos positivos. Los correos del dominio corporativo de ejemplo (empresa.com) se permiten: son datos de
prueba de las propias reglas de negocio, no personas reales.
"""
import re
from dataclasses import dataclass

DOMINIOS_PERMITIDOS = ("empresa.com",)


def _luhn(numero: str) -> bool:
    digitos = [int(d) for d in re.sub(r"\D", "", numero)][::-1]
    total = sum(d if i % 2 == 0 else (d * 2 - 9 if d * 2 > 9 else d * 2) for i, d in enumerate(digitos))
    return len(digitos) >= 13 and total % 10 == 0


DETECTORES: list[tuple[str, re.Pattern, callable]] = [
    # secretos primero: un token puede contener secuencias que parecen otros datos
    ("llave_api", re.compile(r"\b(?:sk-ant-[A-Za-z0-9_\-]{10,}|lsv2_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{20,}"
                             r"|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9\-]{10,})"), lambda m: True),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\b"), lambda m: True),
    ("correo", re.compile(r"\b[A-Za-z0-9._%+\-]+@([A-Za-z0-9.\-]+\.[A-Za-z]{2,})\b"),
     lambda m: m.group(1).lower() not in DOMINIOS_PERMITIDOS),
    ("curp", re.compile(r"\b[A-Z][AEIOUX][A-Z]{2}\d{6}[HM][A-Z]{5}[A-Z0-9]\d\b"), lambda m: True),
    ("rfc", re.compile(r"\b[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}\b"), lambda m: True),
    ("tarjeta", re.compile(r"\b(?:\d[ -]?){13,19}\b"), lambda m: _luhn(m.group(0))),
    ("clabe", re.compile(r"\b\d{18}\b"), lambda m: True),
    ("telefono", re.compile(r"(?<!\d)(?:\+?52[ -]?)?(?:\(?\d{2,3}\)?[ -]?)\d{3,4}[ -]?\d{4}(?!\d)"), lambda m: True),
    ("ip", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), lambda m: True),
]


@dataclass
class ResultadoPII:
    texto: str                       # texto con los hallazgos enmascarados
    hallazgos: dict[str, int]        # tipo -> cantidad (nunca el valor encontrado)

    @property
    def hay(self) -> bool:
        return bool(self.hallazgos)


def enmascarar(texto: str) -> ResultadoPII:
    """Sustituye cada hallazgo por [TIPO] y cuenta cuántos hubo de cada tipo."""
    hallazgos: dict[str, int] = {}
    for tipo, patron, valido in DETECTORES:
        def reemplazo(m, tipo=tipo, valido=valido):
            if m.group(0).startswith("[") or not valido(m):
                return m.group(0)
            hallazgos[tipo] = hallazgos.get(tipo, 0) + 1
            return f"[{tipo.upper()}]"
        texto = patron.sub(reemplazo, texto)
    return ResultadoPII(texto, hallazgos)
