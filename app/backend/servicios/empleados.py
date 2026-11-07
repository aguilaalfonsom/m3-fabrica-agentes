"""Lógica de negocio de empleados (fuera de los routers)."""
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pydantic import ValidationError

from esquemas import EmpleadoBaja, EmpleadoCrear, EmpleadoEditar
from modelos import Empleado


def _siguiente_numero(db: Session) -> str:
    maximo = db.scalar(select(func.max(Empleado.numero_empleado)))
    consecutivo = int(maximo.split("-")[1]) + 1 if maximo else 1
    return f"EMP-{consecutivo:04d}"


def crear_empleado(db: Session, datos: EmpleadoCrear) -> Empleado:
    # El correo ya viene en minúsculas desde el esquema.
    existente = db.scalar(select(Empleado).where(func.lower(Empleado.correo) == datos.correo))
    if existente:
        raise HTTPException(status_code=409, detail="El correo ya está registrado")
    empleado = Empleado(numero_empleado=_siguiente_numero(db), **datos.model_dump())
    db.add(empleado)
    db.commit()
    db.refresh(empleado)
    return empleado


def listar_empleados(
    db: Session, buscar: str | None = None, departamento: str | None = None
) -> list[Empleado]:
    consulta = select(Empleado).order_by(Empleado.id)
    if departamento:
        consulta = consulta.where(Empleado.departamento == departamento)
    empleados = list(db.scalars(consulta))
    texto = (buscar or "").strip().casefold()
    if texto:
        # SQLite solo baja a minúsculas ASCII; se compara en Python para soportar acentos.
        empleados = [
            e for e in empleados if texto in e.nombre.casefold() or texto in e.correo.casefold()
        ]
    return empleados


MSG_BAJA = "No se puede editar a un empleado dado de baja"


def obtener_empleado(db: Session, empleado_id: int) -> Empleado:
    empleado = db.get(Empleado, empleado_id)
    if not empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return empleado


def editar_empleado(db: Session, empleado_id: int, cuerpo: dict) -> Empleado:
    # Orden: 404, 409 (de baja) y por último 422; por eso el cuerpo se valida aquí.
    empleado = obtener_empleado(db, empleado_id)
    if empleado.estado == "baja":
        raise HTTPException(status_code=409, detail=MSG_BAJA)
    try:
        datos = EmpleadoEditar.model_validate(cuerpo)
    except ValidationError as exc:
        loc = exc.errors()[0]["loc"]
        detail = f"Corrige el campo {loc[-1]}" if loc else "Cuerpo de la solicitud inválido"
        raise HTTPException(status_code=422, detail=detail)
    empleado.puesto = datos.puesto
    empleado.departamento = datos.departamento
    db.commit()
    db.refresh(empleado)
    return empleado


def dar_de_baja(db: Session, empleado_id: int, datos: EmpleadoBaja) -> Empleado:
    empleado = obtener_empleado(db, empleado_id)
    if empleado.estado == "baja":
        raise HTTPException(status_code=409, detail=MSG_BAJA)
    if datos.fecha_baja < empleado.fecha_ingreso:
        raise HTTPException(status_code=422, detail="Corrige el campo fecha_baja")
    empleado.estado = "baja"
    empleado.fecha_baja = datos.fecha_baja
    db.commit()
    db.refresh(empleado)
    return empleado
