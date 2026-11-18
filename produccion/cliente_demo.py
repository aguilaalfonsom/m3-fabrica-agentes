"""Cliente de demostración de la API (lee las llaves de .env; nunca las imprime).

Uso:
  python -m produccion.cliente_demo criterios historias/HU-10-solicitar-vacaciones.md [--url URL]
  python -m produccion.cliente_demo concurrencia 6 [--url URL]
  python -m produccion.cliente_demo seguridad [--url URL]
"""
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

from produccion.config import RAIZ

sys.stdout.reconfigure(encoding="utf-8")
URL = sys.argv[sys.argv.index("--url") + 1] if "--url" in sys.argv else os.environ.get("API_URL", "http://127.0.0.1:8000")
LLAVES = dict(reversed(p.split(":", 1)) for p in os.environ.get("API_KEYS", "").split(",") if ":" in p)
ROL = {v: k for k, v in LLAVES.items()}           # rol -> llave
CLIENTE = {"X-API-Key": ROL.get("cliente", "")}
TIEMPO = httpx.Timeout(300.0)


def resumen(r: httpx.Response) -> str:
    try:
        c = r.json()
    except ValueError:
        return f"{r.status_code} {r.text[:120]}"
    if r.status_code != 200:
        return f"{r.status_code} {json.dumps(c.get('detail', c), ensure_ascii=False)[:200]}"
    agentes = ", ".join(f"{a['agente']}={a['modelo'].replace('claude-', '')} ${a['costo_usd']:.4f}" for a in c["agentes"])
    return (f"200 {c['hu']} · {c['gherkin'].count('Escenario:')} escenarios · {len(c['casos'])} casos · "
            f"${c['costo_usd']:.4f} · {c['latencia_ms'] / 1000:.1f} s · caché={c['desde_cache']}"
            + (f"\n      agentes: {agentes}" if agentes else "") + f"\n      request_id={c['request_id']}")


def criterios(ruta: str) -> None:
    historia = (RAIZ / ruta).read_text(encoding="utf-8")
    r = httpx.post(f"{URL}/v1/criterios", json={"historia": historia}, headers=CLIENTE, timeout=TIEMPO)
    print(f"POST /v1/criterios ({Path(ruta).name}) -> {resumen(r)}")


def concurrencia(n: int) -> None:
    base = (RAIZ / "historias" / "HU-02-consultar-directorio.md").read_text(encoding="utf-8")
    inicio = time.time()

    def una(i):
        h = base + f"\n- Variante de carga {uuid.uuid4().hex[:6]}"
        t = time.time()
        r = httpx.post(f"{URL}/v1/criterios", json={"historia": h}, headers=CLIENTE, timeout=TIEMPO)
        return i, r, time.time() - t

    with ThreadPoolExecutor(max_workers=n) as pool:
        for i, r, s in pool.map(una, range(n)):
            print(f"  petición {i + 1}: {r.status_code} en {s:.1f} s · X-Request-ID={r.headers.get('X-Request-ID')}")
    print(f"{n} peticiones concurrentes en {time.time() - inicio:.1f} s")


def seguridad() -> None:
    hu10 = (RAIZ / "historias" / "HU-10-solicitar-vacaciones.md").read_text(encoding="utf-8")
    casos = [
        ("Sin API key", lambda: httpx.post(f"{URL}/v1/criterios", json={"historia": hu10}, timeout=TIEMPO)),
        ("Rol lector intenta generar", lambda: httpx.post(f"{URL}/v1/criterios", json={"historia": hu10},
                                                          headers={"X-API-Key": ROL.get("lector", "")}, timeout=TIEMPO)),
        ("Entrada inválida (no es historia)", lambda: httpx.post(f"{URL}/v1/criterios", json={"historia": "x" * 50},
                                                                 headers=CLIENTE, timeout=TIEMPO)),
        ("Historia envenenada HU-99", lambda: httpx.post(
            f"{URL}/v1/criterios", json={"historia": (RAIZ / "historias" / "HU-99-envenenada.md").read_text(encoding="utf-8")},
            headers=CLIENTE, timeout=TIEMPO)),
        ("Historia con PII (correo, teléfono, CURP)", lambda: httpx.post(
            f"{URL}/v1/criterios", headers=CLIENTE, timeout=TIEMPO, json={"historia":
                "# HU-01 · Registrar empleado\n\nComo persona de RH, quiero registrar a juan.perez@gmail.com "
                "(tel 55 1234 5678, CURP GOMC800101HDFRRL09), para darlo de alta.\n\n- Correo único."})),
    ]
    for nombre, f in casos:
        r = f()
        extra = ""
        if r.status_code == 200:
            extra = f" · PII enmascarada: {r.json()['pii_enmascarada']}"
        print(f"  {nombre}: {resumen(r).splitlines()[0]}{extra}")


if __name__ == "__main__":
    accion = sys.argv[1]
    if accion == "criterios":
        criterios(sys.argv[2])
    elif accion == "concurrencia":
        concurrencia(int(sys.argv[2]))
    elif accion == "seguridad":
        seguridad()
