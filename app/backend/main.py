"""Aplicación FastAPI. Cada historia nueva agrega su router en ROUTERS."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

import modelos  # noqa: F401  (registra las tablas)
from database import Base, motor
from esquemas import MSG_CORREO, MSG_FECHA_FUTURA
from routers import empleados, vacaciones

Base.metadata.create_all(motor)

app = FastAPI(title="Gestión de empleados")

ROUTERS = [empleados.router, vacaciones.router]
for r in ROUTERS:
    app.include_router(r, prefix="/api")

ETIQUETAS = {"fecha_ingreso": "fecha de ingreso"}


@app.get("/api/salud")
def salud():
    return {"estado": "ok"}


@app.exception_handler(RequestValidationError)
async def errores_validacion(request: Request, exc: RequestValidationError):
    """Convierte los errores de Pydantic al formato {"detail": "..."} con 422."""
    primero = exc.errors()[0]
    mensaje = str(primero.get("msg", ""))
    campo = str(primero["loc"][-1]) if primero["loc"] else ""
    if mensaje.endswith(MSG_FECHA_FUTURA):
        detail = MSG_FECHA_FUTURA
    elif mensaje.endswith(MSG_CORREO):
        detail = MSG_CORREO
    elif campo in ("body", ""):
        detail = "Cuerpo de la solicitud inválido"
    else:
        detail = f"Corrige el campo {ETIQUETAS.get(campo, campo)}"
    return JSONResponse(status_code=422, content={"detail": detail})
