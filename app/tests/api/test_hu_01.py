"""Pruebas de API de HU-01 (registrar empleado).

Nota: la API no ofrece forma de vaciar la base, así que los tests no suponen
«base sin empleados»: usan correos únicos y comparan contra lo que ya existe.
"""
import re
import uuid
from datetime import date, timedelta

import httpx
import pytest

MSG_DUPLICADO = "El correo ya está registrado"
MSG_DOMINIO = "Usa el correo corporativo @empresa.com"
MSG_FUTURA = "La fecha de ingreso no puede ser futura"
PATRON_NUMERO = re.compile(r"^EMP-\d{4,}$")


@pytest.fixture
def cliente(url_api):
    with httpx.Client(base_url=url_api, timeout=10) as c:
        yield c


def correo_unico(prefijo: str = "prueba") -> str:
    return f"{prefijo}.{uuid.uuid4().hex[:12]}@empresa.com"


def datos_validos(**cambios) -> dict:
    datos = {
        "nombre": "Ana Pérez",
        "correo": correo_unico("ana"),
        "puesto": "Analista",
        "departamento": "Tecnología",
        "fecha_ingreso": "2026-01-15",
    }
    datos.update(cambios)
    return datos


def listar(cliente) -> list[dict]:
    r = cliente.get("/api/empleados")
    assert r.status_code == 200
    return r.json()


def numero(emp: dict) -> int:
    return int(emp["numero_empleado"].split("-")[1])


def assert_rechazo(cliente, datos: dict, detail: str | None = None):
    """422/409 y no se crea ningún empleado."""
    antes = len(listar(cliente))
    r = cliente.post("/api/empleados", json=datos)
    assert r.status_code == 422, r.text
    if detail:
        assert r.json()["detail"] == detail
    assert len(listar(cliente)) == antes


def test_cp_01(cliente):
    """CP-01: Registro exitoso del primer empleado"""
    datos = datos_validos()
    r = cliente.post("/api/empleados", json=datos)
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert PATRON_NUMERO.match(cuerpo["numero_empleado"])
    assert cuerpo["estado"] == "activo"
    assert cuerpo["fecha_baja"] is None
    assert cuerpo["creado_en"]
    assert cuerpo["correo"] == datos["correo"]


def test_cp_02(cliente):
    """CP-02: El listado contiene al empleado con su número y estado activo"""
    datos = datos_validos()
    r = cliente.post("/api/empleados", json=datos)
    assert r.status_code == 201, r.text
    creado = r.json()
    encontrados = [e for e in listar(cliente) if e["correo"] == datos["correo"]]
    assert len(encontrados) == 1
    assert encontrados[0]["numero_empleado"] == creado["numero_empleado"]
    assert PATRON_NUMERO.match(encontrados[0]["numero_empleado"])
    assert encontrados[0]["estado"] == "activo"


def test_cp_04(cliente):
    """CP-04: El número de empleado es consecutivo"""
    r1 = cliente.post("/api/empleados", json=datos_validos())
    assert r1.status_code == 201, r1.text
    r2 = cliente.post(
        "/api/empleados",
        json=datos_validos(nombre="Luis Gómez", puesto="Vendedor", departamento="Ventas",
                           fecha_ingreso="2026-02-02", correo=correo_unico("luis")),
    )
    assert r2.status_code == 201, r2.text
    assert numero(r2.json()) == numero(r1.json()) + 1
    assert PATRON_NUMERO.match(r2.json()["numero_empleado"])


def test_cp_05(cliente):
    """CP-05: El número lo asigna el sistema aunque se envíe uno"""
    datos = datos_validos()
    datos["numero_empleado"] = "EMP-0999"
    r = cliente.post("/api/empleados", json=datos)
    assert r.status_code == 201, r.text
    assert r.json()["numero_empleado"] != "EMP-0999"
    assert PATRON_NUMERO.match(r.json()["numero_empleado"])


def test_cp_06(cliente):
    """CP-06: El correo se guarda en minúsculas"""
    sufijo = uuid.uuid4().hex[:12]
    r = cliente.post(
        "/api/empleados",
        json=datos_validos(nombre="Marta Ruiz", departamento="Finanzas",
                           fecha_ingreso="2026-03-01", correo=f"Marta.Ruiz.{sufijo}@empresa.com"),
    )
    assert r.status_code == 201, r.text
    assert r.json()["correo"] == f"marta.ruiz.{sufijo}@empresa.com"


def test_cp_07(cliente):
    """CP-07: Departamento "Recursos Humanos" del catálogo es aceptado"""
    r = cliente.get("/api/departamentos")
    assert r.status_code == 200
    assert "Recursos Humanos" in r.json()
    r = cliente.post(
        "/api/empleados",
        json=datos_validos(nombre="Eva Soto", puesto="Reclutadora",
                           departamento="Recursos Humanos", fecha_ingreso="2026-03-10"),
    )
    assert r.status_code == 201, r.text
    assert r.json()["departamento"] == "Recursos Humanos"


def _crear_base(cliente) -> dict:
    datos = datos_validos()
    r = cliente.post("/api/empleados", json=datos)
    assert r.status_code == 201, r.text
    return datos


def test_cp_08(cliente):
    """CP-08: Correo duplicado con el mismo texto"""
    base = _crear_base(cliente)
    antes = len(listar(cliente))
    r = cliente.post(
        "/api/empleados",
        json=datos_validos(nombre="Carla Núñez", correo=base["correo"], fecha_ingreso="2026-04-01"),
    )
    assert r.status_code == 409, r.text
    assert r.json()["detail"] == MSG_DUPLICADO
    assert len(listar(cliente)) == antes


def test_cp_09(cliente):
    """CP-09: Correo duplicado sin importar mayúsculas"""
    base = _crear_base(cliente)
    r = cliente.post(
        "/api/empleados",
        json=datos_validos(nombre="Carla Núñez", correo=base["correo"].upper().replace("@EMPRESA.COM", "@empresa.com"),
                           fecha_ingreso="2026-04-01"),
    )
    assert r.status_code == 409, r.text
    assert r.json()["detail"] == MSG_DUPLICADO


def test_cp_10(cliente):
    """CP-10: El error de correo duplicado llega con el detail esperado"""
    base = _crear_base(cliente)
    r = cliente.post(
        "/api/empleados",
        json=datos_validos(nombre="Carla Núñez", correo=base["correo"], fecha_ingreso="2026-04-01"),
    )
    assert r.status_code == 409, r.text
    assert r.json()["detail"] == MSG_DUPLICADO


def test_cp_12(cliente):
    """CP-12: Correo con dominio distinto al corporativo"""
    assert_rechazo(cliente, datos_validos(correo=f"ana.{uuid.uuid4().hex[:8]}@gmail.com"), MSG_DOMINIO)


def test_cp_13(cliente):
    """CP-13: Correo sin arroba ni dominio"""
    assert_rechazo(cliente, datos_validos(correo="ana.perez"), MSG_DOMINIO)


def test_cp_14(cliente):
    """CP-14: El error de dominio de correo llega con el detail esperado"""
    assert_rechazo(cliente, datos_validos(correo=f"ana.{uuid.uuid4().hex[:8]}@otraempresa.com"), MSG_DOMINIO)


def test_cp_16(cliente):
    """CP-16: Fecha de ingreso de hoy es válida (límite)"""
    r = cliente.post("/api/empleados", json=datos_validos(fecha_ingreso=date.today().isoformat()))
    assert r.status_code == 201, r.text


def test_cp_17(cliente):
    """CP-17: Fecha de ingreso de mañana ya no es válida (límite)"""
    manana = (date.today() + timedelta(days=1)).isoformat()
    assert_rechazo(cliente, datos_validos(fecha_ingreso=manana), MSG_FUTURA)


def test_cp_18(cliente):
    """CP-18: Fecha de ingreso en el pasado es válida"""
    r = cliente.post("/api/empleados", json=datos_validos(fecha_ingreso="2025-12-21"))
    assert r.status_code == 201, r.text


def test_cp_19(cliente):
    """CP-19: El error de fecha futura llega con el detail esperado"""
    futura = (date.today() + timedelta(days=25)).isoformat()
    assert_rechazo(cliente, datos_validos(fecha_ingreso=futura), MSG_FUTURA)


def test_cp_21(cliente):
    """CP-21: Nombre de 2 caracteres es válido (límite)"""
    r = cliente.post("/api/empleados", json=datos_validos(nombre="Li"))
    assert r.status_code == 201, r.text


def test_cp_22(cliente):
    """CP-22: Nombre de 1 carácter no es válido (límite)"""
    assert_rechazo(cliente, datos_validos(nombre="L"))


def test_cp_24(cliente):
    """CP-24: Nombre de 80 caracteres es válido (límite)"""
    r = cliente.post("/api/empleados", json=datos_validos(nombre="A" * 80))
    assert r.status_code == 201, r.text


def test_cp_25(cliente):
    """CP-25: Nombre de 81 caracteres no es válido (límite)"""
    assert_rechazo(cliente, datos_validos(nombre="A" * 81))


def test_cp_27(cliente):
    """CP-27: Nombre vacío"""
    assert_rechazo(cliente, datos_validos(nombre=""))


def test_cp_29(cliente):
    """CP-29: Puesto de 2 caracteres es válido (límite)"""
    r = cliente.post("/api/empleados", json=datos_validos(puesto="TI"))
    assert r.status_code == 201, r.text


def test_cp_30(cliente):
    """CP-30: Puesto de 1 carácter no es válido (límite)"""
    assert_rechazo(cliente, datos_validos(puesto="T"))


def test_cp_32(cliente):
    """CP-32: Puesto de 60 caracteres es válido (límite)"""
    r = cliente.post("/api/empleados", json=datos_validos(puesto="B" * 60))
    assert r.status_code == 201, r.text


def test_cp_33(cliente):
    """CP-33: Puesto de 61 caracteres no es válido (límite)"""
    assert_rechazo(cliente, datos_validos(puesto="B" * 61))


def test_cp_35(cliente):
    """CP-35: Puesto vacío"""
    assert_rechazo(cliente, datos_validos(puesto=""))


def test_cp_37(cliente):
    """CP-37: Departamento fuera del catálogo"""
    assert_rechazo(cliente, datos_validos(departamento="Marketing"))


def test_cp_39(cliente):
    """CP-39: Correo vacío"""
    assert_rechazo(cliente, datos_validos(correo=""))


def test_cp_41(cliente):
    """CP-41: Fecha de ingreso vacía"""
    assert_rechazo(cliente, datos_validos(fecha_ingreso=""))
