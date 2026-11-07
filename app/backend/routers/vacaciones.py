"""Rutas de vacaciones."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import obtener_db
from esquemas_vacaciones import SaldoSalida, VacacionCrear, VacacionSalida
from servicios import vacaciones as servicio

router = APIRouter()


@router.post(
    "/empleados/{empleado_id}/vacaciones", status_code=201, response_model=VacacionSalida
)
def solicitar(empleado_id: int, datos: VacacionCrear, db: Session = Depends(obtener_db)):
    return servicio.registrar_solicitud(db, empleado_id, datos)


@router.get("/empleados/{empleado_id}/vacaciones", response_model=SaldoSalida)
def saldo(empleado_id: int, anio: int | None = None, db: Session = Depends(obtener_db)):
    return servicio.consultar_saldo(db, empleado_id, anio)
