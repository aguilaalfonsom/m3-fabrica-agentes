"""Pruebas E2E de HU-01 (registrar empleado) con pytest-playwright."""
import re
import uuid
from datetime import date, timedelta

import httpx
from playwright.sync_api import Page, expect

MSG_DUPLICADO = "El correo ya está registrado"
MSG_DOMINIO = "Usa el correo corporativo @empresa.com"
MSG_FUTURA = "La fecha de ingreso no puede ser futura"


def correo_unico(prefijo: str = "e2e") -> str:
    return f"{prefijo}.{uuid.uuid4().hex[:12]}@empresa.com"


def abrir_formulario(page: Page, url_web: str) -> None:
    page.goto(url_web)
    expect(page.get_by_test_id("empleado-guardar")).to_be_visible()


def llenar(page: Page, **campos) -> None:
    """Llena el formulario con datos válidos; `campos` sobreescribe cada valor."""
    datos = {
        "nombre": "Ana Pérez",
        "correo": correo_unico(),
        "puesto": "Analista",
        "departamento": "Tecnología",
        "fecha_ingreso": "2026-01-15",
    }
    datos.update(campos)
    page.get_by_test_id("empleado-nombre").fill(datos["nombre"])
    page.get_by_test_id("empleado-correo").fill(datos["correo"])
    page.get_by_test_id("empleado-puesto").fill(datos["puesto"])
    if datos["departamento"]:
        page.get_by_test_id("empleado-departamento").select_option(datos["departamento"])
    if datos["fecha_ingreso"]:
        page.get_by_test_id("empleado-fecha-ingreso").fill(datos["fecha_ingreso"])


def verificar_error_campo(page: Page, campo: str) -> None:
    mensaje = page.get_by_test_id("mensaje-error")
    expect(mensaje).to_be_visible()
    expect(mensaje).to_contain_text(re.compile(rf"campo {re.escape(campo)}", re.I))


def test_cp_03(page: Page, url_web):
    """CP-03: La pantalla muestra confirmación con el número asignado"""
    correo = correo_unico("ana")
    abrir_formulario(page, url_web)
    llenar(page, correo=correo)
    page.get_by_test_id("empleado-guardar").click()
    exito = page.get_by_test_id("mensaje-exito")
    expect(exito).to_be_visible()
    expect(exito).to_contain_text(re.compile(r"EMP-\d{4,}"))
    numero = re.search(r"EMP-\d{4,}", exito.inner_text()).group(0)
    fila = page.get_by_test_id("tabla-empleados").locator("tr", has_text=correo)
    expect(fila).to_have_count(1)
    id_fila = fila.get_attribute("data-testid").removeprefix("fila-empleado-")
    expect(page.get_by_test_id(f"numero-empleado-{id_fila}")).to_have_text(numero)
    expect(page.get_by_test_id(f"estado-empleado-{id_fila}")).to_have_text("Activo")


def test_cp_11(page: Page, url_web, url_api):
    """CP-11: La pantalla muestra el error de correo duplicado"""
    correo = correo_unico("ana")
    r = httpx.post(f"{url_api}/api/empleados", json={
        "nombre": "Ana Pérez", "correo": correo, "puesto": "Analista",
        "departamento": "Tecnología", "fecha_ingreso": "2026-01-15"}, timeout=10)
    assert r.status_code == 201, r.text
    abrir_formulario(page, url_web)
    llenar(page, nombre="Carla Núñez", correo=correo, fecha_ingreso="2026-04-01")
    page.get_by_test_id("empleado-guardar").click()
    expect(page.get_by_test_id("mensaje-error")).to_contain_text(MSG_DUPLICADO)


def test_cp_15(page: Page, url_web):
    """CP-15: La pantalla muestra el error de dominio de correo"""
    abrir_formulario(page, url_web)
    llenar(page, correo=f"ana.{uuid.uuid4().hex[:8]}@otraempresa.com")
    page.get_by_test_id("empleado-guardar").click()
    expect(page.get_by_test_id("mensaje-error")).to_contain_text(MSG_DOMINIO)


def test_cp_20(page: Page, url_web):
    """CP-20: La pantalla muestra el error de fecha futura"""
    abrir_formulario(page, url_web)
    llenar(page, fecha_ingreso=(date.today() + timedelta(days=25)).isoformat())
    page.get_by_test_id("empleado-guardar").click()
    expect(page.get_by_test_id("mensaje-error")).to_contain_text(MSG_FUTURA)


def test_cp_23(page: Page, url_web):
    """CP-23: Nombre de 1 carácter no es válido (límite)"""
    abrir_formulario(page, url_web)
    llenar(page, nombre="L", correo=correo_unico("l"))
    page.get_by_test_id("empleado-guardar").click()
    verificar_error_campo(page, "nombre")


def test_cp_26(page: Page, url_web):
    """CP-26: Nombre de 81 caracteres no es válido (límite)"""
    abrir_formulario(page, url_web)
    llenar(page, nombre="A" * 81)
    page.get_by_test_id("empleado-guardar").click()
    verificar_error_campo(page, "nombre")


def test_cp_28(page: Page, url_web):
    """CP-28: Nombre vacío"""
    abrir_formulario(page, url_web)
    llenar(page, nombre="")
    page.get_by_test_id("empleado-guardar").click()
    verificar_error_campo(page, "nombre")


def test_cp_31(page: Page, url_web):
    """CP-31: Puesto de 1 carácter no es válido (límite)"""
    abrir_formulario(page, url_web)
    llenar(page, puesto="T")
    page.get_by_test_id("empleado-guardar").click()
    verificar_error_campo(page, "puesto")


def test_cp_34(page: Page, url_web):
    """CP-34: Puesto de 61 caracteres no es válido (límite)"""
    abrir_formulario(page, url_web)
    llenar(page, puesto="B" * 61)
    page.get_by_test_id("empleado-guardar").click()
    verificar_error_campo(page, "puesto")


def test_cp_36(page: Page, url_web):
    """CP-36: Puesto vacío"""
    abrir_formulario(page, url_web)
    llenar(page, puesto="")
    page.get_by_test_id("empleado-guardar").click()
    verificar_error_campo(page, "puesto")


def test_cp_38(page: Page, url_web):
    """CP-38: Departamento fuera del catálogo (se deja sin elegir en el selector)"""
    abrir_formulario(page, url_web)
    llenar(page, departamento="")
    page.get_by_test_id("empleado-guardar").click()
    verificar_error_campo(page, "departamento")


def test_cp_40(page: Page, url_web):
    """CP-40: Correo vacío"""
    abrir_formulario(page, url_web)
    llenar(page, correo="")
    page.get_by_test_id("empleado-guardar").click()
    verificar_error_campo(page, "correo")


def test_cp_42(page: Page, url_web):
    """CP-42: Fecha de ingreso vacía"""
    abrir_formulario(page, url_web)
    llenar(page, fecha_ingreso="")
    page.get_by_test_id("empleado-guardar").click()
    verificar_error_campo(page, "fecha de ingreso")
