"""Benchmark de costos: baseline vs. optimizado con las mismas historias, midiendo costo Y calidad.

    baseline   : todo con el modelo fuerte, contexto completo, sin caché
    optimizado : ruteo (Haiku en filtro y diseñador, cascada a Sonnet), contexto recortado y caché

La calidad se mide con los mismos validadores deterministas de producción: criterios válidos (incluidos
los mensajes exactos), casos que cubren todos los escenarios, intentos necesarios. Así el ahorro no se
compra con peor resultado sin que se note.

Uso:  python -m produccion.benchmark_costos [HU-01 HU-02 ...]
Salida: docs/costos/benchmark.json, docs/costos/grafica_costos.svg y la tabla en consola.
Con la cuenta personal, el costo es el precio de lista que reporta el SDK por cada llamada.
"""
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from produccion.config import RAIZ, config

sys.stdout.reconfigure(encoding="utf-8")
SALIDA = RAIZ / "docs" / "costos"
MODOS = {
    "baseline": {"RUTEO_ACTIVO": "false", "CONTEXTO_RECORTADO": "false", "CACHE_ACTIVO": "false"},
    "optimizado": {"RUTEO_ACTIVO": "true", "CONTEXTO_RECORTADO": "true", "CACHE_ACTIVO": "true"},
}


def _historias(ids: list[str]) -> dict[str, str]:
    archivos = {p.name.split("-", 2)[0] + "-" + p.name.split("-", 2)[1]: p for p in (RAIZ / "historias").glob("HU-*.md")}
    return {hu: archivos[hu].read_text(encoding="utf-8") for hu in ids}


def correr(modo: str, hu: str, historia: str) -> dict:
    from agentes.analista import validar_gherkin
    from agentes.disenador_pruebas import validar_plan
    from produccion import cache
    from produccion.grafo import grafo

    inicio = time.perf_counter()
    k = cache.clave(historia)
    guardado = cache.leer(k)
    if guardado:
        return {"modo": modo, "hu": hu, "costo_usd": 0.0, "latencia_s": round(time.perf_counter() - inicio, 2),
                "desde_cache": True, "escenarios": guardado["gherkin"].count("Escenario:"),
                "casos": len(guardado["casos"]), "criterios_validos": True, "casos_validos": True, "llamadas": []}
    estado = grafo.invoke({"historia": historia}, config={
        "run_name": f"benchmark {modo} {hu}", "tags": ["benchmark", f"benchmark:{modo}"],
        "metadata": {"modo": modo, "hu": hu}})
    gherkin, plan = estado.get("gherkin", ""), estado.get("plan", {"casos": []})
    fila = {"modo": modo, "hu": hu, "costo_usd": round(estado.get("costo_usd", 0.0), 6),
            "latencia_s": round(time.perf_counter() - inicio, 2), "desde_cache": False,
            "resultado": estado.get("resultado"), "escenarios": gherkin.count("Escenario:"), "casos": len(plan["casos"]),
            "criterios_validos": not validar_gherkin(gherkin, hu), "casos_validos": not validar_plan(json.dumps(plan), gherkin),
            "intentos_analista": estado.get("intentos_analista"), "intentos_disenador": estado.get("intentos_disenador"),
            "llamadas": [{k2: u[k2] for k2 in ("agente", "modelo", "input_tokens", "output_tokens", "costo_usd")}
                         for u in estado.get("usos", [])]}
    if estado.get("resultado") == "ok":
        cache.guardar(k, {"hu": hu, "gherkin": gherkin, "casos": plan["casos"], "preguntas_abiertas": [],
                          "pii_enmascarada": {}}, fila["costo_usd"])
    return fila


def modo(nombre: str, historias: dict[str, str]) -> list[dict]:
    os.environ.update(MODOS[nombre])
    config.cache_clear()
    print(f"\n== {nombre}: {config().publica()['estrategias']}")
    with ThreadPoolExecutor(max_workers=len(historias)) as pool:
        filas = list(pool.map(lambda par: correr(nombre, *par), historias.items()))
    for f in filas:
        print(f"  {f['hu']}: ${f['costo_usd']:.4f} · {f['latencia_s']} s · {f['escenarios']} esc · {f['casos']} casos · "
              f"válidos={f['criterios_validos'] and f['casos_validos']} · caché={f['desde_cache']}")
    return filas


def grafica_svg(resumen: dict) -> str:
    barras = [("Baseline", resumen["baseline"], "#94a3b8"), ("Optimizado (1.ª vez)", resumen["optimizado"], "#38bdf8"),
              ("Optimizado (repetida, caché)", resumen["optimizado_cache"], "#4ade80")]
    maximo = max(v for _, v, _ in barras) or 1
    alto, ancho_barra, x0 = 260, 150, 70
    partes = [f'<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" font-family="Segoe UI, sans-serif">',
              '<rect width="640" height="360" fill="#ffffff"/>',
              '<text x="320" y="28" text-anchor="middle" font-size="16" font-weight="600" fill="#0f172a">'
              'Costo de LLM por lote de 4 historias (USD, precio de lista)</text>']
    for i, (nombre, valor, color) in enumerate(barras):
        h = alto * valor / maximo
        x = x0 + i * (ancho_barra + 40)
        partes.append(f'<rect x="{x}" y="{310 - h:.1f}" width="{ancho_barra}" height="{h:.1f}" rx="6" fill="{color}"/>')
        partes.append(f'<text x="{x + ancho_barra / 2}" y="{302 - h:.1f}" text-anchor="middle" font-size="15" '
                      f'font-weight="600" fill="#0f172a">${valor:.3f}</text>')
        partes.append(f'<text x="{x + ancho_barra / 2}" y="332" text-anchor="middle" font-size="12" fill="#334155">{nombre}</text>')
    partes.append('<line x1="50" y1="310" x2="610" y2="310" stroke="#cbd5e1"/></svg>')
    return "\n".join(partes)


def main(ids: list[str]) -> None:
    historias = _historias(ids)
    os.environ["DIR_DATOS"] = str(RAIZ / "produccion" / "datos" / "benchmark")
    config.cache_clear()
    from produccion import cache
    (config().dir_datos / "cache.sqlite").unlink(missing_ok=True)      # caché limpia: medición justa
    base = modo("baseline", historias)
    opt = modo("optimizado", historias)
    opt_cache = modo("optimizado", historias)                          # mismas historias otra vez: caché
    for f in opt_cache:
        f["modo"] = "optimizado_cache"
    total = lambda filas: round(sum(f["costo_usd"] for f in filas), 6)  # noqa: E731
    resumen = {"baseline": total(base), "optimizado": total(opt), "optimizado_cache": total(opt_cache)}
    resumen["ahorro_primera_vez_pct"] = round(100 * (1 - resumen["optimizado"] / resumen["baseline"]), 1)
    resumen["ahorro_con_cache_pct"] = round(100 * (1 - (resumen["optimizado"] + resumen["optimizado_cache"])
                                                  / (2 * resumen["baseline"])), 1)
    resumen["calidad"] = {m: {"validos": sum(f["criterios_validos"] and f["casos_validos"] for f in filas),
                              "escenarios": sum(f["escenarios"] for f in filas), "casos": sum(f["casos"] for f in filas)}
                          for m, filas in (("baseline", base), ("optimizado", opt))}
    SALIDA.mkdir(parents=True, exist_ok=True)
    (SALIDA / "benchmark.json").write_text(json.dumps({"resumen": resumen, "filas": base + opt + opt_cache,
                                                       "fecha": time.strftime("%Y-%m-%d %H:%M")},
                                                      ensure_ascii=False, indent=2), encoding="utf-8")
    (SALIDA / "grafica_costos.svg").write_text(grafica_svg(resumen), encoding="utf-8")
    print("\nResumen:", json.dumps(resumen, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:] or ["HU-01", "HU-02", "HU-03", "HU-10"])
