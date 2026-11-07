"""Esquemas Pydantic de vacaciones."""
from datetime import date

from pydantic import BaseModel, ConfigDict


class VacacionCrear(BaseModel):
    fecha_inicio: date
    fecha_fin: date


class VacacionSalida(BaseModel):
    id: int
    empleado_id: int
    fecha_inicio: date
    fecha_fin: date
    dias_habiles: int
    dias_restantes: int


class SolicitudSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha_inicio: date
    fecha_fin: date
    dias_habiles: int


class SaldoSalida(BaseModel):
    empleado_id: int
    anio: int
    dias_usados: int
    dias_disponibles: int
    solicitudes: list[SolicitudSalida]
