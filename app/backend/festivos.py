"""Festivos oficiales (LFT art. 74) y conteo de días hábiles."""
from datetime import date, timedelta

FESTIVOS: dict[int, set[date]] = {
    2026: {
        date(2026, 1, 1), date(2026, 2, 2), date(2026, 3, 16), date(2026, 5, 1),
        date(2026, 9, 16), date(2026, 11, 16), date(2026, 12, 25),
    },
    2027: {
        date(2027, 1, 1), date(2027, 2, 1), date(2027, 3, 15), date(2027, 5, 1),
        date(2027, 9, 16), date(2027, 11, 15), date(2027, 12, 25),
    },
}


def contar_dias_habiles(inicio: date, fin: date) -> int:
    """Cuenta los días entre inicio y fin (ambos incluidos) que no son fin de semana ni festivo."""
    total = 0
    dia = inicio
    while dia <= fin:
        if dia.weekday() < 5 and dia not in FESTIVOS.get(dia.year, set()):
            total += 1
        dia += timedelta(days=1)
    return total
