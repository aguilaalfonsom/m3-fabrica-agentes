"""Pruebas de API de HU-10 (solicitud de vacaciones) con pytest y httpx.

Cada test crea sus propios empleados con correo único (uuid) y fecha_ingreso fija,
así no depende de la fecha de hoy ni de otros datos. Los ids 7, 8 y 10 de los casos
son ilustrativos: aquí se usa el id real que devuelve la API.
Empleado «antiguo»: ingreso 2024-03-10. Empleado «nuevo»: ingreso 2025-12-21.
"""
import uuid

import httpx
import pytest

INGRESO_ANTIGUO = "2024-03-10"
INGRESO_NUEVO = "2025-12-21"

MSG_SIN_HABILES = "El periodo no incluye días hábiles"
MSG_ANTIGUEDAD = "Se requiere al menos un año de antigüedad a la fecha de inicio"
MSG_BAJA = "No se pueden solicitar vacaciones para un empleado dado de baja"


@pytest.fixture()
def cliente(url_api):
    with httpx.Client(base_url=url_api, timeout=10) as c:
        yield c


def crear(cliente, ingreso: str = INGRESO_ANTIGUO) -> dict:
    r = cliente.post("/api/empleados", json={
        "nombre": "Ana Torres",
        "correo": f"ana.torres.{uuid.uuid4().hex[:10]}@empresa.com",
        "puesto": "Analista",
        "departamento": "Ventas",
        "fecha_ingreso": ingreso,
    })
    assert r.status_code == 201, r.text
    return r.json()


def solicitar(cliente, emp_id, inicio: str, fin: str) -> httpx.Response:
    return cliente.post(f"/api/empleados/{emp_id}/vacaciones",
                        json={"fecha_inicio": inicio, "fecha_fin": fin})


def usar(cliente, emp: dict, inicio: str, fin: str, dias: int) -> None:
    """Precondición: registra una solicitud válida que consume `dias` días hábiles."""
    r = solicitar(cliente, emp["id"], inicio, fin)
    assert r.status_code == 201, r.text
    assert r.json()["dias_habiles"] == dias


def saldo(cliente, emp: dict, anio: int) -> httpx.Response:
    return cliente.get(f"/api/empleados/{emp['id']}/vacaciones", params={"anio": anio})


def esperar_201(r, emp, inicio, fin, habiles, restantes) -> None:
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["empleado_id"] == emp["id"]
    assert cuerpo["fecha_inicio"] == inicio
    assert cuerpo["fecha_fin"] == fin
    assert cuerpo["dias_habiles"] == habiles
    assert cuerpo["dias_restantes"] == restantes


def esperar_error(r, codigo: int, detail: str) -> None:
    assert r.status_code == codigo, r.text
    assert r.json()["detail"] == detail


def crear_baja(cliente) -> dict:
    emp = crear(cliente)
    rb = cliente.post(f"/api/empleados/{emp['id']}/baja", json={"fecha_baja": "2026-01-05"})
    assert rb.status_code == 200, rb.text
    return emp


def test_cp_01(cliente):
    """CP-01: Solicitud válida por API descuenta solo días hábiles"""
    emp = crear(cliente)
    r = solicitar(cliente, emp["id"], "2026-07-06", "2026-07-10")
    esperar_201(r, emp, "2026-07-06", "2026-07-10", 5, 7)


def test_cp_03(cliente):
    """CP-03: Consultar el saldo del año tras una solicitud"""
    emp = crear(cliente)
    usar(cliente, emp, "2026-12-21", "2026-12-31", 8)
    r = saldo(cliente, emp, 2026)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["dias_usados"] == 8
    assert cuerpo["dias_disponibles"] == 4
    assert len(cuerpo["solicitudes"]) == 1
    s = cuerpo["solicitudes"][0]
    assert s["fecha_inicio"] == "2026-12-21"
    assert s["fecha_fin"] == "2026-12-31"
    assert s["dias_habiles"] == 8


def test_cp_04(cliente):
    """CP-04: Saldo de un año sin solicitudes"""
    emp = crear(cliente)
    r = saldo(cliente, emp, 2027)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["dias_usados"] == 0
    assert cuerpo["dias_disponibles"] == 12
    assert cuerpo["solicitudes"] == []


def test_cp_05(cliente):
    """CP-05: Un día festivo dentro del periodo no se descuenta"""
    emp = crear(cliente)
    r = solicitar(cliente, emp["id"], "2026-09-14", "2026-09-18")
    esperar_201(r, emp, "2026-09-14", "2026-09-18", 4, 8)


def test_cp_06(cliente):
    """CP-06: Fines de semana y Navidad no se descuentan"""
    emp = crear(cliente)
    r = solicitar(cliente, emp["id"], "2026-12-21", "2026-12-31")
    esperar_201(r, emp, "2026-12-21", "2026-12-31", 8, 4)


def test_cp_07(cliente):
    """CP-07: Un festivo de 2027 también se excluye"""
    emp = crear(cliente)
    r = solicitar(cliente, emp["id"], "2027-09-13", "2027-09-17")
    esperar_201(r, emp, "2027-09-13", "2027-09-17", 4, 8)


def test_cp_08(cliente):
    """CP-08: Un solo día hábil cuenta como 1 día"""
    emp = crear(cliente)
    r = solicitar(cliente, emp["id"], "2026-07-06", "2026-07-06")
    esperar_201(r, emp, "2026-07-06", "2026-07-06", 1, 11)


def test_cp_09(cliente):
    """CP-09: Periodo de sábado y domingo se rechaza"""
    emp = crear(cliente)
    r = solicitar(cliente, emp["id"], "2026-07-11", "2026-07-12")
    esperar_error(r, 400, MSG_SIN_HABILES)


def test_cp_10(cliente):
    """CP-10: Periodo formado solo por un festivo en sábado y un domingo se rechaza"""
    emp = crear(cliente)
    r = solicitar(cliente, emp["id"], "2027-05-01", "2027-05-02")
    esperar_error(r, 400, MSG_SIN_HABILES)


def test_cp_11(cliente):
    """CP-11: Periodo de un solo día festivo se rechaza"""
    emp = crear(cliente)
    r = solicitar(cliente, emp["id"], "2026-09-16", "2026-09-16")
    esperar_error(r, 400, MSG_SIN_HABILES)


def test_cp_12(cliente):
    """CP-12: Cumple exactamente un año de antigüedad el día de inicio"""
    emp = crear(cliente, INGRESO_NUEVO)
    r = solicitar(cliente, emp["id"], "2026-12-21", "2026-12-31")
    esperar_201(r, emp, "2026-12-21", "2026-12-31", 8, 4)


def test_cp_13(cliente):
    """CP-13: Le faltan días para cumplir un año"""
    emp = crear(cliente, INGRESO_NUEVO)
    r = solicitar(cliente, emp["id"], "2026-12-18", "2026-12-18")
    esperar_error(r, 400, MSG_ANTIGUEDAD)


def test_cp_14(cliente):
    """CP-14: Falta un solo día para cumplir un año"""
    emp = crear(cliente, INGRESO_NUEVO)
    r = solicitar(cliente, emp["id"], "2026-12-20", "2026-12-22")
    esperar_error(r, 400, MSG_ANTIGUEDAD)


def test_cp_15(cliente):
    """CP-15: La antigüedad se valida antes que los días hábiles"""
    emp = crear(cliente, INGRESO_NUEVO)
    r = solicitar(cliente, emp["id"], "2026-07-11", "2026-07-12")
    esperar_error(r, 400, MSG_ANTIGUEDAD)


def test_cp_16(cliente):
    """CP-16: Usar exactamente los días que quedan"""
    emp = crear(cliente)
    usar(cliente, emp, "2026-07-06", "2026-07-10", 5)
    r = solicitar(cliente, emp["id"], "2026-07-13", "2026-07-21")
    esperar_201(r, emp, "2026-07-13", "2026-07-21", 7, 0)


def test_cp_17(cliente):
    """CP-17: Pedir un día más de los que quedan"""
    emp = crear(cliente)
    usar(cliente, emp, "2026-08-03", "2026-08-17", 11)
    r = solicitar(cliente, emp["id"], "2026-07-06", "2026-07-07")
    esperar_error(r, 400, "La solicitud excede los días disponibles: quedan 1 días hábiles")


def test_cp_18(cliente):
    """CP-18: Pedir el último día disponible"""
    emp = crear(cliente)
    usar(cliente, emp, "2026-08-03", "2026-08-17", 11)
    r = solicitar(cliente, emp["id"], "2026-07-06", "2026-07-06")
    esperar_201(r, emp, "2026-07-06", "2026-07-06", 1, 0)


def test_cp_19(cliente):
    """CP-19: Solicitud que rebasa el saldo"""
    emp = crear(cliente)
    usar(cliente, emp, "2026-07-06", "2026-07-09", 4)
    r = solicitar(cliente, emp["id"], "2026-08-03", "2026-08-13")
    esperar_error(r, 400, "La solicitud excede los días disponibles: quedan 8 días hábiles")


def test_cp_20(cliente):
    """CP-20: Sin días disponibles"""
    emp = crear(cliente)
    usar(cliente, emp, "2026-07-06", "2026-07-21", 12)
    r = solicitar(cliente, emp["id"], "2026-08-03", "2026-08-03")
    esperar_error(r, 400, "La solicitud excede los días disponibles: quedan 0 días hábiles")


def test_cp_21(cliente):
    """CP-21: Un periodo de más de 12 días hábiles con saldo completo se rechaza"""
    emp = crear(cliente)
    r = solicitar(cliente, emp["id"], "2026-08-03", "2026-08-19")
    esperar_error(r, 400, "La solicitud excede los días disponibles: quedan 12 días hábiles")


def test_cp_23(cliente):
    """CP-23: Los días usados en 2026 no afectan el saldo de 2027"""
    emp = crear(cliente)
    usar(cliente, emp, "2026-07-06", "2026-07-21", 12)
    r = solicitar(cliente, emp["id"], "2027-07-05", "2027-07-09")
    esperar_201(r, emp, "2027-07-05", "2027-07-09", 5, 7)


def test_cp_24(cliente):
    """CP-24: Fecha de fin anterior a la de inicio"""
    emp = crear(cliente)
    r = solicitar(cliente, emp["id"], "2026-07-10", "2026-07-06")
    esperar_error(r, 400, "La fecha de fin no puede ser anterior a la fecha de inicio")


def test_cp_25(cliente):
    """CP-25: Periodo que cruza de un año a otro"""
    emp = crear(cliente)
    r = solicitar(cliente, emp["id"], "2026-12-28", "2027-01-08")
    esperar_error(r, 400, "Las vacaciones deben estar dentro de un mismo año calendario")


def test_cp_26(cliente):
    """CP-26: Año fuera de la tabla de festivos"""
    emp = crear(cliente)
    r = solicitar(cliente, emp["id"], "2028-01-10", "2028-01-14")
    esperar_error(r, 400, "Solo se pueden solicitar vacaciones en 2026 y 2027")


def test_cp_27(cliente):
    """CP-27: Año anterior a la tabla de festivos"""
    emp = crear(cliente)
    r = solicitar(cliente, emp["id"], "2025-12-15", "2025-12-19")
    esperar_error(r, 400, "Solo se pueden solicitar vacaciones en 2026 y 2027")


def test_cp_28(cliente):
    """CP-28: Empleado que no existe"""
    r = solicitar(cliente, 9999, "2026-07-06", "2026-07-10")
    esperar_error(r, 404, "Empleado no encontrado")


def test_cp_29(cliente):
    """CP-29: Empleado dado de baja"""
    emp = crear_baja(cliente)
    r = solicitar(cliente, emp["id"], "2026-07-06", "2026-07-10")
    esperar_error(r, 409, MSG_BAJA)


def test_cp_30(cliente):
    """CP-30: El empleado dado de baja se valida antes que las fechas"""
    emp = crear_baja(cliente)
    r = solicitar(cliente, emp["id"], "2026-07-10", "2026-07-06")
    esperar_error(r, 409, MSG_BAJA)


def test_cp_31(cliente):
    """CP-31: Formato de fecha inválido"""
    emp = crear(cliente)
    r = solicitar(cliente, emp["id"], "10/07/2026", "2026-07-12")
    assert r.status_code == 422, r.text


def test_cp_32(cliente):
    """CP-32: Una solicitud rechazada no descuenta días"""
    emp = crear(cliente)
    usar(cliente, emp, "2026-07-06", "2026-07-09", 4)
    rechazo = solicitar(cliente, emp["id"], "2026-08-03", "2026-08-13")
    assert rechazo.status_code == 400, rechazo.text
    r = saldo(cliente, emp, 2026)
    assert r.status_code == 200, r.text
    assert r.json()["dias_usados"] == 4
    assert r.json()["dias_disponibles"] == 8
