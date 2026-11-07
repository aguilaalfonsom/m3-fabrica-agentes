"""Pruebas E2E de HU-02 (directorio, búsqueda y filtro) con pytest-playwright.

La base es compartida: cada test crea sus empleados por API con un token único
y aísla lo que ve en pantalla escribiendo ese token en el buscador.
"""
import uuid

import httpx
import pytest
from playwright.sync_api import Page, expect


def token() -> str:
    return "zq" + uuid.uuid4().hex[:10]


def crear(url_api: str, nombre: str, correo: str, departamento: str = "Tecnología",
          puesto: str = "Analista") -> dict:
    r = httpx.post(f"{url_api}/api/empleados", json={
        "nombre": nombre, "correo": correo, "puesto": puesto,
        "departamento": departamento, "fecha_ingreso": "2026-01-15"}, timeout=10)
    assert r.status_code == 201, r.text
    return r.json()


def cuatro(url_api: str, t: str) -> dict[str, dict]:
    return {
        "ana": crear(url_api, f"Ana Pérez {t}", f"ana.perez.{t}@empresa.com", "Tecnología", "Desarrolladora"),
        "luis": crear(url_api, f"Luis Gómez {t}", f"luis.gomez.{t}@empresa.com", "Ventas", "Vendedor"),
        "marta": crear(url_api, f"Marta Ruiz {t}", f"marta.ruiz.{t}@empresa.com", "Finanzas", "Contadora"),
        "torres": crear(url_api, f"Beto Torres {t}", f"atorres.{t}@empresa.com", "Finanzas", "Auditor"),
    }


def abrir(page: Page, url_web: str) -> None:
    page.goto(url_web)
    expect(page.get_by_test_id("tabla-empleados")).to_be_visible()


def fila(page: Page, emp: dict):
    return page.get_by_test_id(f"fila-empleado-{emp['id']}")


def buscar(page: Page, texto: str) -> None:
    page.get_by_test_id("buscar-empleados").fill(texto)


def solo_visible(page: Page, visibles: list[dict], todos: dict[str, dict]) -> None:
    for e in todos.values():
        if any(e["id"] == v["id"] for v in visibles):
            expect(fila(page, e)).to_be_visible()
        else:
            expect(fila(page, e)).to_have_count(0)


def filas_tabla(page: Page):
    return page.get_by_test_id("tabla-empleados").locator("tbody tr")


def test_cp_02(page: Page, url_web, url_api):
    """CP-02: Ver el directorio completo"""
    t = token()
    emps = cuatro(url_api, t)
    abrir(page, url_web)
    for e in emps.values():
        expect(fila(page, e)).to_be_visible()
    ana = fila(page, emps["ana"])
    for texto in [emps["ana"]["numero_empleado"], f"Ana Pérez {t}", "Desarrolladora", "Tecnología", "Activo"]:
        expect(ana).to_contain_text(texto)
    expect(page.get_by_test_id(f"numero-empleado-{emps['luis']['id']}")).to_have_text(emps["luis"]["numero_empleado"])


def test_cp_04(page: Page, url_web):
    """CP-04: Un empleado dado de baja sigue apareciendo en el directorio"""
    pytest.skip("No hay forma de dar de baja un empleado (HU-03 no implementada)")


def test_cp_07(page: Page, url_web, url_api):
    """CP-07: Buscar por nombre"""
    t = token()
    emps = cuatro(url_api, t)
    abrir(page, url_web)
    buscar(page, f"Luis Gómez {t}")
    solo_visible(page, [emps["luis"]], emps)


def test_cp_09(page: Page, url_web, url_api):
    """CP-09: Buscar por correo"""
    t = token()
    emps = cuatro(url_api, t)
    abrir(page, url_web)
    buscar(page, f"marta.ruiz.{t}@empresa.com")
    solo_visible(page, [emps["marta"]], emps)


def test_cp_11(page: Page, url_web, url_api):
    """CP-11: La búsqueda por nombre no distingue mayúsculas en mayúsculas"""
    t = token()
    emps = cuatro(url_api, t)
    abrir(page, url_web)
    buscar(page, f"LUIS GÓMEZ {t}".upper())
    solo_visible(page, [emps["luis"]], emps)


def test_cp_13(page: Page, url_web, url_api):
    """CP-13: La búsqueda por nombre no distingue mayúsculas en minúsculas"""
    t = token()
    emps = cuatro(url_api, t)
    abrir(page, url_web)
    buscar(page, f"luis gómez {t}")
    solo_visible(page, [emps["luis"]], emps)


def test_cp_15(page: Page, url_web, url_api):
    """CP-15: La búsqueda por correo no distingue mayúsculas de minúsculas"""
    t = token()
    emps = cuatro(url_api, t)
    abrir(page, url_web)
    buscar(page, f"ATORRES.{t}@EMPRESA.COM".upper())
    solo_visible(page, [emps["torres"]], emps)


def test_cp_17(page: Page, url_web, url_api):
    """CP-17: La búsqueda por texto parcial devuelve varias coincidencias"""
    t = token()
    ana = crear(url_api, f"Ana Pérez {t}", f"ana.perez.{t}@empresa.com")
    mariana = crear(url_api, f"Mariana Soto {t}", f"msoto.{t}@empresa.com", "Ventas")
    luis = crear(url_api, f"Luis Gómez {t}", f"luis.gomez.{t}@empresa.com", "Ventas")
    abrir(page, url_web)
    buscar(page, "ana")
    expect(fila(page, ana)).to_be_visible()
    expect(fila(page, mariana)).to_be_visible()
    expect(fila(page, luis)).to_have_count(0)


def test_cp_19(page: Page, url_web, url_api):
    """CP-19: Filtrar por departamento"""
    emps = cuatro(url_api, token())
    abrir(page, url_web)
    page.get_by_test_id("filtro-departamento").select_option("Ventas")
    expect(fila(page, emps["luis"])).to_be_visible()
    for k in ("ana", "marta", "torres"):
        expect(fila(page, emps[k])).to_have_count(0)


def test_cp_21(page: Page, url_web, url_api):
    """CP-21: Filtrar por un departamento válido sin empleados"""
    t = token()
    cuatro(url_api, t)
    abrir(page, url_web)
    # Aislado con el token: ninguno de estos empleados está en Operaciones.
    buscar(page, t)
    page.get_by_test_id("filtro-departamento").select_option("Operaciones")
    expect(filas_tabla(page)).to_have_count(0)
    expect(page.get_by_test_id("sin-resultados")).to_be_visible()


def test_cp_23(page: Page, url_web, url_api):
    """CP-23: Combinar búsqueda y filtro de departamento"""
    t = token()
    emps = cuatro(url_api, t)
    otra = crear(url_api, f"Ana Díaz {t}", f"ana.diaz.{t}@empresa.com", "Ventas")
    abrir(page, url_web)
    buscar(page, "ana")
    page.get_by_test_id("filtro-departamento").select_option("Tecnología")
    expect(fila(page, emps["ana"])).to_be_visible()
    expect(fila(page, otra)).to_have_count(0)


def test_cp_25(page: Page, url_web, url_api):
    """CP-25: Búsqueda y filtro sin coincidencia conjunta"""
    t = token()
    cuatro(url_api, t)
    abrir(page, url_web)
    buscar(page, f"Luis Gómez {t}")
    page.get_by_test_id("filtro-departamento").select_option("Finanzas")
    expect(filas_tabla(page)).to_have_count(0)
    expect(page.get_by_test_id("sin-resultados")).to_be_visible()


def test_cp_27(page: Page, url_web, url_api):
    """CP-27: Búsqueda sin resultados muestra un mensaje"""
    cuatro(url_api, token())
    abrir(page, url_web)
    buscar(page, f"Zacarías {token()}")
    expect(filas_tabla(page)).to_have_count(0)
    expect(page.get_by_test_id("sin-resultados")).to_be_visible()


def test_cp_29(page: Page, url_web, url_api):
    """CP-29: Limpiar la búsqueda restaura el directorio"""
    emps = cuatro(url_api, token())
    abrir(page, url_web)
    buscar(page, f"Zacarías {token()}")
    expect(page.get_by_test_id("sin-resultados")).to_be_visible()
    buscar(page, "")
    expect(page.get_by_test_id("sin-resultados")).to_have_count(0)
    for e in emps.values():
        expect(fila(page, e)).to_be_visible()


def test_cp_31(page: Page, url_web, url_api):
    """CP-31: El mensaje de sin resultados no aparece cuando hay coincidencias"""
    t = token()
    ana = crear(url_api, f"Ana Pérez {t}", f"ana.perez.{t}@empresa.com")
    abrir(page, url_web)
    buscar(page, "Ana")
    expect(fila(page, ana)).to_be_visible()
    expect(page.get_by_test_id("sin-resultados")).to_have_count(0)


def test_cp_33(page: Page, url_web):
    """CP-33: Directorio vacío"""
    pytest.skip("La API no permite vaciar la base: no se puede garantizar un directorio sin empleados")
