"""Pruebas de API de HU-02 (directorio, búsqueda y filtro de empleados).

La base es compartida y la API no permite vaciarla ni dar de baja empleados,
así que cada test crea sus propios empleados con un token único en nombre y
correo, y aísla las búsquedas con ese token. Los casos que exigen una base
vacía o un empleado dado de baja se omiten con el motivo (pytest.skip).
"""
import uuid

import httpx
import pytest

CAMPOS = ["id", "numero_empleado", "nombre", "correo", "puesto", "departamento",
          "fecha_ingreso", "estado", "fecha_baja", "creado_en"]


@pytest.fixture
def cliente(url_api):
    with httpx.Client(base_url=url_api, timeout=10) as c:
        yield c


def token() -> str:
    return "zq" + uuid.uuid4().hex[:10]


def crear(cliente, nombre: str, correo: str, departamento: str = "Tecnología",
          puesto: str = "Analista") -> dict:
    r = cliente.post("/api/empleados", json={
        "nombre": nombre, "correo": correo, "puesto": puesto,
        "departamento": departamento, "fecha_ingreso": "2026-01-15"})
    assert r.status_code == 201, r.text
    return r.json()


def listar(cliente, **params) -> list[dict]:
    r = cliente.get("/api/empleados", params=params)
    assert r.status_code == 200, r.text
    return r.json()


def ids(lista: list[dict]) -> set[int]:
    return {e["id"] for e in lista}


def cuatro(cliente, t: str) -> dict[str, dict]:
    """Crea el equivalente del antecedente: Ana, Luis, Marta y un cuarto empleado."""
    return {
        "ana": crear(cliente, f"Ana Pérez {t}", f"ana.perez.{t}@empresa.com", "Tecnología", "Desarrolladora"),
        "luis": crear(cliente, f"Luis Gómez {t}", f"luis.gomez.{t}@empresa.com", "Ventas", "Vendedor"),
        "marta": crear(cliente, f"Marta Ruiz {t}", f"marta.ruiz.{t}@empresa.com", "Finanzas", "Contadora"),
        "torres": crear(cliente, f"Beto Torres {t}", f"atorres.{t}@empresa.com", "Finanzas", "Auditor"),
    }


def test_cp_01(cliente):
    """CP-01: Ver el directorio completo"""
    t = token()
    emps = cuatro(cliente, t)
    lista = listar(cliente)
    por_id = {e["id"]: e for e in lista}
    assert len(lista) >= 4
    ana = por_id[emps["ana"]["id"]]
    assert ana["numero_empleado"].startswith("EMP-")
    assert (ana["nombre"], ana["puesto"], ana["departamento"], ana["estado"]) == \
        (f"Ana Pérez {t}", "Desarrolladora", "Tecnología", "activo")
    assert por_id[emps["luis"]["id"]]["numero_empleado"] == emps["luis"]["numero_empleado"]


def test_cp_03(cliente):
    """CP-03: Un empleado dado de baja sigue apareciendo en el directorio"""
    pytest.skip("La API no ofrece forma de dar de baja un empleado (HU-03 no implementada)")


def test_cp_05(cliente):
    """CP-05: Consultar el directorio por API"""
    emps = cuatro(cliente, token())
    lista = listar(cliente)
    por_id = {e["id"]: e for e in lista}
    assert len(lista) >= 4
    for e in emps.values():
        assert set(CAMPOS) <= set(por_id[e["id"]].keys())


def test_cp_06(cliente):
    """CP-06: Buscar por nombre"""
    t = token()
    emps = cuatro(cliente, t)
    assert ids(listar(cliente, buscar=f"Luis Gómez {t}")) == {emps["luis"]["id"]}
    assert emps["luis"]["id"] in ids(listar(cliente, buscar="Luis"))
    assert emps["ana"]["id"] not in ids(listar(cliente, buscar="Luis"))


def test_cp_08(cliente):
    """CP-08: Buscar por correo"""
    t = token()
    emps = cuatro(cliente, t)
    assert ids(listar(cliente, buscar=f"marta.ruiz.{t}@empresa.com")) == {emps["marta"]["id"]}


def test_cp_10(cliente):
    """CP-10: La búsqueda por nombre no distingue mayúsculas en mayúsculas"""
    t = token()
    emps = cuatro(cliente, t)
    assert ids(listar(cliente, buscar=f"LUIS GÓMEZ {t}".upper())) == {emps["luis"]["id"]}


def test_cp_12(cliente):
    """CP-12: La búsqueda por nombre no distingue mayúsculas en minúsculas"""
    t = token()
    emps = cuatro(cliente, t)
    assert ids(listar(cliente, buscar=f"luis gómez {t}")) == {emps["luis"]["id"]}


def test_cp_14(cliente):
    """CP-14: La búsqueda por correo no distingue mayúsculas de minúsculas"""
    t = token()
    emps = cuatro(cliente, t)
    assert ids(listar(cliente, buscar=f"ATORRES.{t}@EMPRESA.COM".upper())) == {emps["torres"]["id"]}


def test_cp_16(cliente):
    """CP-16: La búsqueda por texto parcial devuelve varias coincidencias"""
    t = token()
    ana = crear(cliente, f"Ana Pérez {t}", f"ana.perez.{t}@empresa.com")
    mariana = crear(cliente, f"Mariana Soto {t}", f"msoto.{t}@empresa.com", "Ventas")
    luis = crear(cliente, f"Luis Gómez {t}", f"luis.gomez.{t}@empresa.com", "Ventas")
    encontrados = ids(listar(cliente, buscar="ana"))
    assert {ana["id"], mariana["id"]} <= encontrados
    assert luis["id"] not in encontrados


def test_cp_18(cliente):
    """CP-18: Filtrar por departamento"""
    emps = cuatro(cliente, token())
    lista = listar(cliente, departamento="Ventas")
    assert emps["luis"]["id"] in ids(lista)
    assert not ({emps["ana"]["id"], emps["marta"]["id"], emps["torres"]["id"]} & ids(lista))
    assert all(e["departamento"] == "Ventas" for e in lista)


def test_cp_20(cliente):
    """CP-20: Filtrar por un departamento válido sin empleados"""
    t = token()
    cuatro(cliente, t)
    r = cliente.get("/api/departamentos")
    assert r.status_code == 200
    assert "Operaciones" in r.json()
    # Aislado con el token: ningún empleado de esta prueba está en Operaciones.
    assert listar(cliente, buscar=t, departamento="Operaciones") == []


def test_cp_22(cliente):
    """CP-22: Combinar búsqueda y filtro de departamento"""
    t = token()
    emps = cuatro(cliente, t)
    otra_ana = crear(cliente, f"Ana Díaz {t}", f"ana.diaz.{t}@empresa.com", "Ventas")
    res = listar(cliente, buscar="ana", departamento="Tecnología")
    assert emps["ana"]["id"] in ids(res)
    assert otra_ana["id"] not in ids(res)
    assert all(e["departamento"] == "Tecnología" for e in res)


def test_cp_24(cliente):
    """CP-24: Búsqueda y filtro sin coincidencia conjunta"""
    t = token()
    cuatro(cliente, t)
    assert listar(cliente, buscar=f"Luis Gómez {t}", departamento="Finanzas") == []


def test_cp_26(cliente):
    """CP-26: Búsqueda sin resultados muestra un mensaje"""
    cuatro(cliente, token())
    assert listar(cliente, buscar=f"Zacarías {token()}") == []


def test_cp_28(cliente):
    """CP-28: Limpiar la búsqueda restaura el directorio"""
    emps = cuatro(cliente, token())
    assert listar(cliente, buscar=f"Zacarías {token()}") == []
    assert {e["id"] for e in emps.values()} <= ids(listar(cliente))


def test_cp_30(cliente):
    """CP-30: El mensaje de sin resultados no aparece cuando hay coincidencias"""
    t = token()
    ana = crear(cliente, f"Ana Pérez {t}", f"ana.perez.{t}@empresa.com")
    mariana = crear(cliente, f"Mariana Soto {t}", f"msoto.{t}@empresa.com", "Ventas")
    res = listar(cliente, buscar="Ana")
    assert len(res) >= 2
    assert {ana["id"], mariana["id"]} <= ids(res)


def test_cp_32(cliente):
    """CP-32: Directorio vacío"""
    pytest.skip("La API no permite vaciar la base: no se puede garantizar un directorio sin empleados")
