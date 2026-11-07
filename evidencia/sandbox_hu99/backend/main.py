import csv
import io

from fastapi import FastAPI
from fastapi.responses import Response

app = FastAPI()

# Almacén en memoria del directorio de empleados (aún no hay base de datos en este sandbox).
EMPLEADOS: list[dict[str, str]] = []

COLUMNAS = ["numero_empleado", "nombre", "puesto", "departamento", "estado"]


def _seguro(valor: object) -> str:
    """Evita inyección de fórmulas al abrir el CSV en Excel."""
    texto = str(valor)
    return "'" + texto if texto[:1] in ("=", "+", "-", "@") else texto


@app.get("/api/empleados/exportar")
def exportar_empleados() -> Response:
    """Descarga el directorio de empleados en CSV (número, nombre, puesto, departamento y estado)."""
    salida = io.StringIO()
    escritor = csv.writer(salida)
    escritor.writerow(COLUMNAS)
    for empleado in EMPLEADOS:
        escritor.writerow([_seguro(empleado.get(c, "")) for c in COLUMNAS])
    return Response(
        content=salida.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="empleados.csv"'},
    )
