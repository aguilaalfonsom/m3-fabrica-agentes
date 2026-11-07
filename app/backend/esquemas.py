"""Esquemas Pydantic v2 y validaciones de datos de empleado."""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator

DEPARTAMENTOS = ["Tecnología", "Ventas", "Finanzas", "Recursos Humanos", "Operaciones"]
MSG_CORREO = "Usa el correo corporativo @empresa.com"
MSG_FECHA_FUTURA = "La fecha de ingreso no puede ser futura"


def _texto(valor, minimo: int, maximo: int) -> str:
    if not isinstance(valor, str):
        raise ValueError("texto inválido")
    valor = valor.strip()
    if not minimo <= len(valor) <= maximo:
        raise ValueError("longitud inválida")
    return valor


class EmpleadoCrear(BaseModel):
    # Los campos extra (p. ej. numero_empleado) se ignoran: lo asigna el sistema.
    model_config = ConfigDict(extra="ignore")

    nombre: str
    correo: str
    puesto: str
    departamento: str
    fecha_ingreso: date

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v):
        return _texto(v, 2, 80)

    @field_validator("puesto", mode="before")
    @classmethod
    def validar_puesto(cls, v):
        return _texto(v, 2, 60)

    @field_validator("correo", mode="before")
    @classmethod
    def validar_correo(cls, v):
        if not isinstance(v, str) or not v.strip():
            raise ValueError("correo vacío")
        v = v.strip().lower()
        if not v.endswith("@empresa.com") or len(v) == len("@empresa.com"):
            raise ValueError(MSG_CORREO)
        return v

    @field_validator("departamento")
    @classmethod
    def validar_departamento(cls, v):
        if v not in DEPARTAMENTOS:
            raise ValueError("departamento fuera del catálogo")
        return v

    @field_validator("fecha_ingreso")
    @classmethod
    def validar_fecha(cls, v):
        if v > date.today():
            raise ValueError(MSG_FECHA_FUTURA)
        return v


class EmpleadoEditar(BaseModel):
    # Solo puesto y departamento son editables; el resto de campos se ignora.
    model_config = ConfigDict(extra="ignore")

    puesto: str
    departamento: str

    @field_validator("puesto", mode="before")
    @classmethod
    def validar_puesto(cls, v):
        return _texto(v, 2, 60)

    @field_validator("departamento")
    @classmethod
    def validar_departamento(cls, v):
        if v not in DEPARTAMENTOS:
            raise ValueError("departamento fuera del catálogo")
        return v


class EmpleadoBaja(BaseModel):
    fecha_baja: date


class EmpleadoSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero_empleado: str
    nombre: str
    correo: str
    puesto: str
    departamento: str
    fecha_ingreso: date
    estado: str
    fecha_baja: date | None
    creado_en: datetime
