# Fábrica de software con agentes · Módulo 3

Una cadena de agentes orquestada con **LangGraph** que convierte una historia de usuario en una aplicación de
gestión de empleados (FastAPI + SQLite + React) desplegada y probada (pytest + Playwright), con defensas de
seguridad en cada capa. Este repositorio contiene la entrega del reto **HU-10 · Solicitar vacaciones**.

| # | Agente | Rol del reto | Cómo funciona | Entrega |
| --- | --- | --- | --- | --- |
| 0 | Filtro de seguridad | Guardrail de entrada | Modelo con salida estructurada (`Veredicto`) | Bloquea historias sospechosas |
| 1 | Analista | Especificación | Bucle ReAct con herramientas propias | `salida/HU-xx/criterios.feature` |
| 2 | Diseñador de pruebas | Tester (diseño) | Bucle ReAct + `guardar_casos` (Pydantic) | `salida/HU-xx/casos_prueba.json` |
| 3a | Desarrollador · planificar | **Planificador** | Claude Code, solo lectura | Plan que aprueba una persona |
| 3b | Desarrollador · construir | **Implementador** | Claude Code, edición | `app/backend`, `app/frontend` |
| 4 | Despliegue | Operaciones | Claude Code | `docker-compose.yml`, app en :8080 |
| 5 | Automatizador | **Tester** | Claude Code | `app/tests/api`, `app/tests/e2e` |
| 6 | Triage | **Reviewer** | Modelo con salida estructurada (`Diagnostico`) | Quién corrige; `reporte.md` |

```
historia ─► filtrar_historia ─► analizar ─► (¿preguntas?) ─► disenar_casos ─► planificar ─► aprobar_plan (HITL)
                                                                                     ▲            │
                                                                                     └─rechazado──┤
             ┌───────────────────── construir ◄──────────── aprobado ◄────────────────────────────┘
             ▼
         verificar ──(falla, < MAX_INTENTOS)──► construir
             │ ok
             ├──► desplegar ─┐   (en paralelo, reductor operator.add)
             └──► automatizar┴─► listo ─► pruebas_e2e ─(falla)─► triage ─► corregir_{codigo|pruebas|despliegue}
                                                │ ok                 └─(tras MAX_CICLOS)─► escalar (HITL)
                                                ▼
                                              fin (reporte.md)
```

El diagrama generado por LangGraph queda en `flujos/salidas/grafo_flujo_s4.html`.

## Requisitos

- Python 3.12 o superior (probado con 3.13 en Windows ARM64), Node 20 o superior.
- Claude Code (`claude --version`) y una **cuenta personal de Claude** (Pro o Max). No se necesita clave de API.
- Docker Desktop **opcional**: si no está, la fábrica despliega la misma topología con procesos locales.

## Instalación

### Windows (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m playwright install chromium
copy .env.example .env
claude setup-token        # inicia sesión y copia el token a CLAUDE_CODE_OAUTH_TOKEN en .env
```

### macOS y Linux

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env
claude setup-token        # pega el token en CLAUDE_CODE_OAUTH_TOKEN dentro de .env
```

`.env` nunca se sube al repositorio (está en `.gitignore`).

## Uso

Todo se ejecuta desde la raíz como módulo (en Windows usa `.venv\Scripts\python.exe` en lugar de `python`):

```bash
# La fábrica completa: filtro → criterios → casos → plan aprobado → código → despliegue ‖ pruebas → triage → reporte
python -m flujos.flujo_s4 historias/HU-10-solicitar-vacaciones.md

# Retomar una ejecución en pausa (por ejemplo, la aprobación del plan) gracias al checkpointer en disco
python -m flujos.flujo_s4 historias/HU-10-solicitar-vacaciones.md --reanudar

# Agentes por separado
python -m agentes.analista historias/HU-10-solicitar-vacaciones.md
python -m agentes.disenador_pruebas salida/HU-10/criterios.feature

# Despliegue local sin Docker (lo hace el flujo; también a mano)
python -m flujos.despliegue_local
python -m flujos.despliegue_local detener

# Demostración de seguridad con la historia envenenada HU-99
python -m seguridad.demo_ataque
```

Durante el flujo la terminal se detiene dos veces como máximo para una persona:
1. **Aprobar el plan**: escribe `si` o tus comentarios (el plan se rehace con ellos).
2. **Escalar**: si el triage no resuelve los fallos tras `MAX_CICLOS`, escribe tu nota para el reporte.

La app queda en http://localhost:8080 y la documentación de la API en http://localhost:8000/docs.

## Pruebas

```bash
cd app
python -m pytest tests -q                       # API (httpx) y E2E (Playwright) contra la app desplegada
python -m pytest tests/api -q                   # solo API
URL_API=http://localhost:8000 URL_WEB=http://localhost:8080 python -m pytest tests/e2e -q
```

## Estructura

| Carpeta | Contenido |
| --- | --- |
| `historias/` | Historias de entrada; HU-10 es la del reto, HU-99 la historia envenenada |
| `contexto/` | Reglas de negocio y convenciones (incluyen las de vacaciones al final) |
| `agentes/` | Los agentes; `modelo.py` es la puerta al modelo con la cuenta personal |
| `flujos/` | Grafos LangGraph (`flujo_s2` a `flujo_s4`), verificaciones, persistencia y despliegue local |
| `seguridad/` | Hooks PreToolUse (rol, lectura, comandos, auditoría) y la demostración de ataque |
| `app/` | La aplicación generada por los agentes (no se edita a mano) |
| `salida/HU-xx/` | Pizarra en disco: criterios, casos, resultados, reporte y decisiones |
| `salida/seguridad.md` | Tabla de ataques, capas que los detienen y checklist de producción |
| `evidencia/` | Bitácoras y auditorías de las ejecuciones (incluida la de HU-99) |
| `auditoria.jsonl` | Registro de cada intento de herramienta por agente en la ejecución final |

## Seguridad en una línea por capa

1. **Mínima agencia**: cada agente solo tiene las herramientas de su rol; sin WebFetch ni WebSearch.
2. **Aislamiento**: hooks `confinar_escritura` y `confinar_lectura`; la app corre en contenedores (o procesos locales).
3. **Credenciales**: el token vive en `.env`, nunca en prompts ni en el repositorio.
4. **Guardrails**: `filtrar_historia` y prompts endurecidos con `<historia_no_confiable>`; validadores deterministas.
5. **Humano en el bucle**: aprobación del plan y escalamiento.
6. **Auditoría**: `auditoria.jsonl`.
7. **Límites**: `MAX_INTENTOS`, `MAX_CICLOS`, `max_turns` y presupuesto por llamada.

Ver [`CHANGELOG.md`](CHANGELOG.md) para los cambios de la fábrica y `salida/HU-10/decisiones.md` para las decisiones del reto.
