"""Pruebas E2E de HU-03 (editar y dar de baja) con pytest-playwright.

Cada test crea su empleado por API con correo único (uuid) y fecha_ingreso fija
(2024-03-10); no depende de la fecha de hoy ni de otros datos.
"""
import uuid

import httpx
from playwright.sync_api import Page, expect

INGRESO = "2024-03-10"


def crear(url_api: str, puesto: str = "Analista", departamento: str = "Ventas") -> dict:
    r = httpx.post(f"{url_api}/api/empleados", json={
        "nombre": "Ana Torres",
        "correo": f"ana.torres.{uuid.uuid4().hex[:10]}@empresa.com",
        "puesto": puesto,
        "departamento": departamento,
        "fecha_ingreso": INGRESO,
    }, timeout=10)
    assert r.status_code == 201, r.text
    return r.json()


def abrir(page: Page, url_web: str) -> None:
    page.goto(url_web)
    expect(page.get_by_test_id("tabla-empleados")).to_be_visible()


def fila(page: Page, emp: dict):
    return page.get_by_test_id(f"fila-empleado-{emp['id']}")


def abrir_edicion(page: Page, url_web: str, emp: dict) -> None:
    abrir(page, url_web)
    page.get_by_test_id(f"editar-empleado-{emp['id']}").click()
    expect(page.get_by_test_id("empleado-puesto")).to_have_value(emp["puesto"])


def editar(page: Page, puesto: str, departamento: str) -> None:
    page.get_by_test_id("empleado-puesto").fill(puesto)
    page.get_by_test_id("empleado-departamento").select_option(departamento)
    page.get_by_test_id("empleado-guardar").click()


def dar_baja(page: Page, url_web: str, emp: dict, fecha: str) -> None:
    abrir(page, url_web)
    page.get_by_test_id(f"baja-empleado-{emp['id']}").click()
    page.get_by_test_id("empleado-fecha-baja").fill(fecha)
    page.get_by_test_id("confirmar-baja").click()


def test_cp_02(page: Page, url_web, url_api):
    """CP-02: Cambiar puesto y departamento de un empleado activo"""
    emp = crear(url_api)
    abrir_edicion(page, url_web, emp)
    editar(page, "Líder de Finanzas", "Finanzas")
    expect(page.get_by_test_id("mensaje-exito")).to_have_text("Cambio guardado")
    expect(fila(page, emp)).to_contain_text("Líder de Finanzas")
    expect(fila(page, emp)).to_contain_text("Finanzas")


def test_cp_04(page: Page, url_web, url_api):
    """CP-04: El número de empleado y el correo no cambian al editar"""
    emp = crear(url_api)
    abrir_edicion(page, url_web, emp)
    editar(page, "Líder de Finanzas", "Finanzas")
    expect(page.get_by_test_id("mensaje-exito")).to_be_visible()
    expect(page.get_by_test_id(f"numero-empleado-{emp['id']}")).to_have_text(emp["numero_empleado"])


def test_cp_08(page: Page, url_web, url_api):
    """CP-08: Puesto de 1 carácter es rechazado"""
    emp = crear(url_api)
    abrir_edicion(page, url_web, emp)
    editar(page, "Q", "Tecnología")
    expect(page.get_by_test_id("mensaje-error")).to_contain_text("Corrige el campo puesto")
    expect(fila(page, emp)).to_contain_text("Analista")


def test_cp_10(page: Page, url_web, url_api):
    """CP-10: Puesto de 61 caracteres es rechazado"""
    emp = crear(url_api)
    abrir_edicion(page, url_web, emp)
    editar(page, "A" * 61, "Tecnología")
    expect(page.get_by_test_id("mensaje-error")).to_contain_text("Corrige el campo puesto")
    expect(fila(page, emp)).to_contain_text("Analista")


def test_cp_12(page: Page, url_web, url_api):
    """CP-12: Puesto vacío es rechazado"""
    emp = crear(url_api)
    abrir_edicion(page, url_web, emp)
    editar(page, "", "Tecnología")
    expect(page.get_by_test_id("mensaje-error")).to_contain_text("Corrige el campo puesto")


def test_cp_14(page: Page, url_web, url_api):
    """CP-14: Departamento fuera del catálogo es rechazado"""
    emp = crear(url_api)
    abrir_edicion(page, url_web, emp)
    # El selector no ofrece "Marketing": se agrega la opción por JavaScript para
    # forzar el valor inválido y comprobar que el backend lo rechaza.
    page.get_by_test_id("empleado-departamento").evaluate(
        """(el) => {
            const o = document.createElement('option');
            o.value = 'Marketing'; o.textContent = 'Marketing';
            el.appendChild(o);
            el.value = 'Marketing';
            el.dispatchEvent(new Event('change', { bubbles: true }));
        }"""
    )
    page.get_by_test_id("empleado-guardar").click()
    expect(page.get_by_test_id("mensaje-error")).to_contain_text("Corrige el campo departamento")
    expect(fila(page, emp)).to_contain_text("Ventas")
    expect(fila(page, emp)).not_to_contain_text("Marketing")


def test_cp_17(page: Page, url_web, url_api):
    """CP-17: Dar de baja a un empleado activo"""
    emp = crear(url_api)
    dar_baja(page, url_web, emp, "2026-11-06")
    expect(page.get_by_test_id("mensaje-exito")).to_have_text("Baja registrada")


def test_cp_19(page: Page, url_web, url_api):
    """CP-19: El empleado dado de baja sigue en el directorio marcado como Baja"""
    emp = crear(url_api)
    dar_baja(page, url_web, emp, "2026-11-06")
    expect(page.get_by_test_id("mensaje-exito")).to_be_visible()
    expect(page.get_by_test_id("tabla-empleados").get_by_test_id(f"fila-empleado-{emp['id']}")).to_be_visible()
    expect(page.get_by_test_id(f"estado-empleado-{emp['id']}")).to_have_text("Baja")
    expect(page.get_by_test_id(f"numero-empleado-{emp['id']}")).to_have_text(emp["numero_empleado"])


def test_cp_22(page: Page, url_web, url_api):
    """CP-22: Fecha de baja un día anterior a la fecha de ingreso (primer valor inválido)"""
    emp = crear(url_api)
    dar_baja(page, url_web, emp, "2024-03-09")
    expect(page.get_by_test_id("mensaje-error")).to_contain_text("Corrige el campo fecha_baja")
    expect(page.get_by_test_id(f"estado-empleado-{emp['id']}")).to_have_text("Activo")
