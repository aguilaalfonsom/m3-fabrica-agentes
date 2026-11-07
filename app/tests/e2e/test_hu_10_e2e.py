"""Pruebas E2E de HU-10 (vacaciones) con pytest-playwright.

Cada test crea su empleado por API con correo único (uuid) y fecha_ingreso fija;
no depende de la fecha de hoy. Empleado «antiguo»: ingreso 2024-03-10.
Empleado «nuevo»: ingreso 2025-12-21.
"""
import uuid

import httpx
from playwright.sync_api import Page, expect


def crear(url_api: str, ingreso: str = "2024-03-10") -> dict:
    r = httpx.post(f"{url_api}/api/empleados", json={
        "nombre": "Ana Torres",
        "correo": f"ana.torres.{uuid.uuid4().hex[:10]}@empresa.com",
        "puesto": "Analista",
        "departamento": "Ventas",
        "fecha_ingreso": ingreso,
    }, timeout=10)
    assert r.status_code == 201, r.text
    return r.json()


def usar(url_api: str, emp: dict, inicio: str, fin: str) -> None:
    r = httpx.post(f"{url_api}/api/empleados/{emp['id']}/vacaciones",
                   json={"fecha_inicio": inicio, "fecha_fin": fin}, timeout=10)
    assert r.status_code == 201, r.text


def abrir_directorio(page: Page, url_web: str) -> None:
    page.goto(url_web)
    expect(page.get_by_test_id("tabla-empleados")).to_be_visible()


def abrir_formulario(page: Page, url_web: str, emp: dict) -> None:
    abrir_directorio(page, url_web)
    page.get_by_test_id(f"vacaciones-abrir-{emp['id']}").click()


def enviar(page: Page, inicio: str, fin: str) -> None:
    page.get_by_test_id("vacaciones-fecha-inicio").fill(inicio)
    page.get_by_test_id("vacaciones-fecha-fin").fill(fin)
    page.get_by_test_id("vacaciones-enviar").click()


def test_cp_02(page: Page, url_web, url_api):
    """CP-02: Solicitud válida desde la pantalla muestra el mensaje de éxito"""
    emp = crear(url_api)
    abrir_formulario(page, url_web, emp)
    expect(page.get_by_test_id("vacaciones-disponibles")).to_have_text("12")
    enviar(page, "2026-07-06", "2026-07-10")
    expect(page.get_by_test_id("vacaciones-mensaje")).to_have_text(
        "Solicitud registrada: 5 días hábiles. Te quedan 7 días hábiles en 2026.")
    expect(page.get_by_test_id("vacaciones-disponibles")).to_have_text("7")


def test_cp_22(page: Page, url_web, url_api):
    """CP-22: El error de tope se muestra en la pantalla"""
    emp = crear(url_api)
    usar(url_api, emp, "2026-07-06", "2026-07-21")  # 12 días hábiles
    abrir_formulario(page, url_web, emp)
    enviar(page, "2026-08-03", "2026-08-03")
    expect(page.get_by_test_id("vacaciones-mensaje")).to_have_text(
        "La solicitud excede los días disponibles: quedan 0 días hábiles")
    expect(page.get_by_test_id("vacaciones-disponibles")).to_have_text("0")


def test_cp_33(page: Page, url_web, url_api):
    """CP-33: El botón de vacaciones aparece en empleados activos"""
    emp = crear(url_api)
    abrir_directorio(page, url_web)
    expect(page.get_by_test_id(f"vacaciones-abrir-{emp['id']}")).to_be_visible()


def test_cp_34(page: Page, url_web, url_api):
    """CP-34: Un empleado dado de baja no tiene botón de vacaciones"""
    emp = crear(url_api)
    rb = httpx.post(f"{url_api}/api/empleados/{emp['id']}/baja",
                    json={"fecha_baja": "2026-01-05"}, timeout=10)
    assert rb.status_code == 200, rb.text
    abrir_directorio(page, url_web)
    expect(page.get_by_test_id(f"fila-empleado-{emp['id']}")).to_be_visible()
    expect(page.get_by_test_id(f"vacaciones-abrir-{emp['id']}")).to_have_count(0)


def test_cp_35(page: Page, url_web, url_api):
    """CP-35: El error de antigüedad se muestra en la pantalla"""
    emp = crear(url_api, "2025-12-21")
    abrir_formulario(page, url_web, emp)
    enviar(page, "2026-12-18", "2026-12-18")
    expect(page.get_by_test_id("vacaciones-mensaje")).to_have_text(
        "Se requiere al menos un año de antigüedad a la fecha de inicio")
