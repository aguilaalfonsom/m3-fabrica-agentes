"""Pruebas de API de HU-03 (editar puesto/departamento y dar de baja).

Cada test crea su propio empleado con correo único (uuid) y fecha_ingreso fija
(2024-03-10), así no depende de la fecha de hoy ni de otros datos. El id del
empleado lo asigna la API, por eso no se usa el id 1 literal.
"""
import uuid

import httpx
import pytest

INGRESO = "2024-03-10"


@pytest.fixture
def cliente(url_api):
    with httpx.Client(base_url=url_api, timeout=10) as c:
        yield c


def crear(cliente, puesto: str = "Analista", departamento: str = "Ventas") -> dict:
    r = cliente.post("/api/empleados", json={
        "nombre": "Ana Torres",
        "correo": f"ana.torres.{uuid.uuid4().hex[:10]}@empresa.com",
        "puesto": puesto,
        "departamento": departamento,
        "fecha_ingreso": INGRESO,
    })
    assert r.status_code == 201, r.text
    return r.json()


def editar(cliente, emp: dict, puesto: str, departamento: str) -> httpx.Response:
    return cliente.put(f"/api/empleados/{emp['id']}",
                       json={"puesto": puesto, "departamento": departamento})


def baja(cliente, emp: dict, fecha: str) -> httpx.Response:
    return cliente.post(f"/api/empleados/{emp['id']}/baja", json={"fecha_baja": fecha})


def consultar(cliente, emp: dict) -> dict:
    r = cliente.get(f"/api/empleados/{emp['id']}")
    assert r.status_code == 200, r.text
    return r.json()


def test_cp_01(cliente):
    """CP-01: Cambiar puesto y departamento de un empleado activo"""
    emp = crear(cliente)
    r = editar(cliente, emp, "Líder de Finanzas", "Finanzas")
    assert r.status_code == 200, r.text
    actual = consultar(cliente, emp)
    assert actual["puesto"] == "Líder de Finanzas"
    assert actual["departamento"] == "Finanzas"


def test_cp_03(cliente):
    """CP-03: El número de empleado y el correo no cambian al editar"""
    emp = crear(cliente)
    r = editar(cliente, emp, "Líder de Finanzas", "Finanzas")
    assert r.status_code == 200, r.text
    actual = consultar(cliente, emp)
    assert actual["numero_empleado"] == emp["numero_empleado"]
    assert actual["correo"] == emp["correo"]
    assert actual["nombre"] == "Ana Torres"
    assert actual["fecha_ingreso"] == INGRESO


def test_cp_05(cliente):
    """CP-05: Puesto con el mínimo permitido de 2 caracteres"""
    emp = crear(cliente)
    r = editar(cliente, emp, "QA", "Tecnología")
    assert r.status_code == 200, r.text
    assert consultar(cliente, emp)["puesto"] == "QA"


def test_cp_06(cliente):
    """CP-06: Puesto con el máximo permitido de 60 caracteres"""
    emp = crear(cliente)
    puesto = "A" * 60
    r = editar(cliente, emp, puesto, "Operaciones")
    assert r.status_code == 200, r.text
    guardado = consultar(cliente, emp)["puesto"]
    assert len(guardado) == 60
    assert guardado == puesto


def test_cp_07(cliente):
    """CP-07: Puesto de 1 carácter es rechazado"""
    emp = crear(cliente)
    r = editar(cliente, emp, "Q", "Tecnología")
    assert r.status_code == 422, r.text
    assert consultar(cliente, emp)["puesto"] == "Analista"


def test_cp_09(cliente):
    """CP-09: Puesto de 61 caracteres es rechazado"""
    emp = crear(cliente)
    r = editar(cliente, emp, "A" * 61, "Tecnología")
    assert r.status_code == 422, r.text
    assert consultar(cliente, emp)["puesto"] == "Analista"


def test_cp_11(cliente):
    """CP-11: Puesto vacío es rechazado"""
    emp = crear(cliente)
    r = editar(cliente, emp, "", "Tecnología")
    assert r.status_code == 422, r.text


def test_cp_13(cliente):
    """CP-13: Departamento fuera del catálogo es rechazado"""
    emp = crear(cliente)
    assert "Marketing" not in cliente.get("/api/departamentos").json()
    r = editar(cliente, emp, "Analista", "Marketing")
    assert r.status_code == 422, r.text
    assert consultar(cliente, emp)["departamento"] == "Ventas"


def test_cp_15(cliente):
    """CP-15: Un empleado dado de baja no se puede editar"""
    emp = crear(cliente)
    rb = baja(cliente, emp, "2026-10-01")
    assert rb.status_code == 200, rb.text
    r = editar(cliente, emp, "Gerente", "Finanzas")
    assert r.status_code == 409, r.text
    assert r.json()["detail"] == "No se puede editar a un empleado dado de baja"
    actual = consultar(cliente, emp)
    assert actual["puesto"] == "Analista"
    assert actual["departamento"] == "Ventas"


def test_cp_16(cliente):
    """CP-16: Dar de baja a un empleado activo"""
    emp = crear(cliente)
    r = baja(cliente, emp, "2026-11-06")
    assert r.status_code == 200, r.text
    actual = consultar(cliente, emp)
    assert actual["estado"] == "baja"
    assert actual["fecha_baja"] == "2026-11-06"


def test_cp_18(cliente):
    """CP-18: El empleado dado de baja sigue en el directorio marcado como Baja"""
    emp = crear(cliente)
    assert baja(cliente, emp, "2026-11-06").status_code == 200
    r = cliente.get("/api/empleados")
    assert r.status_code == 200, r.text
    por_id = {e["id"]: e for e in r.json()}
    assert emp["id"] in por_id
    assert por_id[emp["id"]]["estado"] == "baja"


def test_cp_20(cliente):
    """CP-20: Fecha de baja igual a la fecha de ingreso (límite permitido)"""
    emp = crear(cliente)
    r = baja(cliente, emp, INGRESO)
    assert r.status_code == 200, r.text
    actual = consultar(cliente, emp)
    assert actual["estado"] == "baja"
    assert actual["fecha_baja"] == INGRESO


def test_cp_21(cliente):
    """CP-21: Fecha de baja un día anterior a la fecha de ingreso (primer valor inválido)"""
    emp = crear(cliente)
    r = baja(cliente, emp, "2024-03-09")
    assert r.status_code == 422, r.text
    actual = consultar(cliente, emp)
    assert actual["estado"] == "activo"
    assert actual["fecha_baja"] is None


def test_cp_23(cliente):
    """CP-23: Un empleado activo no tiene fecha de baja"""
    emp = crear(cliente)
    actual = consultar(cliente, emp)
    assert actual["estado"] == "activo"
    assert actual["fecha_baja"] is None
