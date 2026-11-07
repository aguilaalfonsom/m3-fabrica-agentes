"""Rutas de empleados y catálogo de departamentos."""
from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from database import obtener_db
from esquemas import DEPARTAMENTOS, EmpleadoBaja, EmpleadoCrear, EmpleadoSalida
from servicios import empleados as servicio

router = APIRouter()


@router.post("/empleados", status_code=201, response_model=EmpleadoSalida)
def crear(datos: EmpleadoCrear, db: Session = Depends(obtener_db)):
    return servicio.crear_empleado(db, datos)


@router.get("/empleados", response_model=list[EmpleadoSalida])
def listar(
    buscar: str | None = None,
    departamento: str | None = None,
    db: Session = Depends(obtener_db),
):
    return servicio.listar_empleados(db, buscar, departamento)


@router.get("/empleados/{empleado_id}", response_model=EmpleadoSalida)
def obtener(empleado_id: int, db: Session = Depends(obtener_db)):
    return servicio.obtener_empleado(db, empleado_id)


@router.put("/empleados/{empleado_id}", response_model=EmpleadoSalida)
def editar(empleado_id: int, cuerpo: dict = Body(...), db: Session = Depends(obtener_db)):
    return servicio.editar_empleado(db, empleado_id, cuerpo)


@router.post("/empleados/{empleado_id}/baja", response_model=EmpleadoSalida)
def baja(empleado_id: int, datos: EmpleadoBaja, db: Session = Depends(obtener_db)):
    return servicio.dar_de_baja(db, empleado_id, datos)


@router.get("/departamentos")
def departamentos() -> list[str]:
    return DEPARTAMENTOS
