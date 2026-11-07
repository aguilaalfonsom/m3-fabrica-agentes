"""Lógica de negocio de vacaciones (HU-10)."""
from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from esquemas_vacaciones import VacacionCrear
from festivos import FESTIVOS, contar_dias_habiles
from modelos import Vacacion
from servicios.empleados import obtener_empleado

TOPE_ANUAL = 12


def _error(codigo: int, detail: str) -> HTTPException:
    return HTTPException(status_code=codigo, detail=detail)


def _aniversario(ingreso: date, anio: int) -> date:
    """Mismo día y mes en `anio`; un 29 de febrero pasa al 1 de marzo si no es bisiesto."""
    try:
        return ingreso.replace(year=anio)
    except ValueError:
        return date(anio, 3, 1)


def _solicitudes_del_anio(db: Session, empleado_id: int, anio: int) -> list[Vacacion]:
    # Un periodo nunca cruza de año, así que basta filtrar por la fecha de inicio.
    consulta = (
        select(Vacacion)
        .where(
            Vacacion.empleado_id == empleado_id,
            Vacacion.fecha_inicio >= date(anio, 1, 1),
            Vacacion.fecha_inicio <= date(anio, 12, 31),
        )
        .order_by(Vacacion.id)
    )
    return list(db.scalars(consulta))


def consultar_saldo(db: Session, empleado_id: int, anio: int | None) -> dict:
    obtener_empleado(db, empleado_id)
    anio = anio or date.today().year
    if not 1 <= anio <= 9999:
        raise _error(422, "Corrige el campo anio")
    solicitudes = _solicitudes_del_anio(db, empleado_id, anio)
    usados = sum(s.dias_habiles for s in solicitudes)
    return {
        "empleado_id": empleado_id,
        "anio": anio,
        "dias_usados": usados,
        "dias_disponibles": max(TOPE_ANUAL - usados, 0),
        "solicitudes": solicitudes,
    }


def registrar_solicitud(db: Session, empleado_id: int, datos: VacacionCrear) -> dict:
    # Se valida en el orden de la tabla de errores: el primero que aplique gana.
    empleado = obtener_empleado(db, empleado_id)
    if empleado.estado == "baja":
        raise _error(409, "No se pueden solicitar vacaciones para un empleado dado de baja")
    inicio, fin = datos.fecha_inicio, datos.fecha_fin
    if fin < inicio:
        raise _error(400, "La fecha de fin no puede ser anterior a la fecha de inicio")
    if inicio.year != fin.year:
        raise _error(400, "Las vacaciones deben estar dentro de un mismo año calendario")
    if inicio.year not in FESTIVOS:
        raise _error(400, "Solo se pueden solicitar vacaciones en 2026 y 2027")
    if inicio < _aniversario(empleado.fecha_ingreso, empleado.fecha_ingreso.year + 1):
        raise _error(400, "Se requiere al menos un año de antigüedad a la fecha de inicio")
    dias = contar_dias_habiles(inicio, fin)
    if dias == 0:
        raise _error(400, "El periodo no incluye días hábiles")
    usados = sum(s.dias_habiles for s in _solicitudes_del_anio(db, empleado_id, inicio.year))
    quedan = max(TOPE_ANUAL - usados, 0)
    if dias > quedan:
        raise _error(400, f"La solicitud excede los días disponibles: quedan {quedan} días hábiles")
    vacacion = Vacacion(
        empleado_id=empleado_id, fecha_inicio=inicio, fecha_fin=fin, dias_habiles=dias
    )
    db.add(vacacion)
    db.commit()
    db.refresh(vacacion)
    return {
        "id": vacacion.id,
        "empleado_id": empleado_id,
        "fecha_inicio": inicio,
        "fecha_fin": fin,
        "dias_habiles": dias,
        "dias_restantes": quedan - dias,
    }
