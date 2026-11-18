# Despliegue de la API de producción

## Requisitos previos

| Herramienta | Versión | Para qué |
|---|---|---|
| Python | 3.12 o 3.13 | Ejecutar la API local (Windows, macOS o Linux) |
| Docker + Compose | 24+ | Opción contenedor (la imagen también se construye en CI) |
| Cuenta de Claude (Pro/Max) | — | `claude setup-token` → `CLAUDE_CODE_OAUTH_TOKEN` |
| Cuenta de LangSmith | — | API key para trazas |
| ngrok | 3.x | URL pública hacia la API local |

## 1. Clonar e instalar

```bash
git clone https://github.com/aguilaalfonsom/m3-fabrica-agentes.git
cd m3-fabrica-agentes
git checkout m4-produccion
python -m venv .venv
# Windows: .venv\Scripts\activate    ·    macOS/Linux: source .venv/bin/activate
pip install -r produccion/requirements-dev.txt
```

## 2. Variables de entorno

```bash
cp .env.example .env        # Windows: copy .env.example .env
```

Llena en `.env` (nunca se versiona):

| Variable | Obligatoria | Valor |
|---|---|---|
| `CLAUDE_CODE_OAUTH_TOKEN` | Sí | Salida de `claude setup-token` |
| `LANGSMITH_API_KEY` | Sí (observabilidad) | smith.langchain.com → Settings → API Keys |
| `LANGSMITH_PROJECT` | No | Proyecto de trazas (por defecto `m4-fabrica-produccion`) |
| `API_KEYS` | Sí | `cliente:<llave>,lector:<llave>`; genera llaves con `python -c "import secrets; print('fab_cli_' + secrets.token_urlsafe(24))"` |
| `NGROK_AUTHTOKEN` | Solo para URL pública | dashboard.ngrok.com → Your Authtoken |
| `MODELO_*`, `RUTEO_ACTIVO`, `CONTEXTO_RECORTADO`, `CACHE_ACTIVO` | No | Ruteo y estrategias de costo (valores por defecto en `.env.example`) |
| `MAX_CONCURRENCIA`, `MAX_EN_COLA`, `TIMEOUT_S`, `LIMITE_POR_MINUTO` | No | Capacidad y límites |

## 3a. Ejecutar local (procesos)

```bash
python -m uvicorn produccion.api:app --host 127.0.0.1 --port 8000
```

- Swagger: http://127.0.0.1:8000/docs · Salud: http://127.0.0.1:8000/health · Panel: http://127.0.0.1:8000/dashboard

## 3b. Ejecutar con Docker

```bash
docker compose up -d --build
docker compose ps            # el estado pasa a "healthy" con el HEALTHCHECK
curl http://localhost:8000/health
```

O la imagen publicada por CI: `docker pull ghcr.io/aguilaalfonsom/m3-fabrica-agentes-api:latest`.

## 4. Exponer con ngrok (URL pública)

```bash
winget install ngrok.ngrok                  # macOS: brew install ngrok
ngrok config add-authtoken <tu authtoken>   # una sola vez
ngrok http 8000
```

ngrok imprime una URL `https://….ngrok-free.app`; la API sigue protegida por `X-API-Key`.

## 5. Probar

```bash
python -m produccion.cliente_demo criterios historias/HU-10-solicitar-vacaciones.md
python -m produccion.cliente_demo seguridad
python -m produccion.cliente_demo concurrencia 6
# contra la URL pública:
python -m produccion.cliente_demo criterios historias/HU-02-consultar-directorio.md --url https://….ngrok-free.app
```

Con curl:

```bash
curl -X POST http://127.0.0.1:8000/v1/criterios \
  -H "Content-Type: application/json" -H "X-API-Key: <llave cliente>" \
  -d '{"historia": "# HU-02 · Directorio\n\nComo persona de RH, quiero buscar empleados, para encontrarlos."}'
```

## 6. Pruebas, benchmark y CI

```bash
python -m pytest produccion/tests -q          # sin red ni credenciales (LLM_FALSO=1)
python -m produccion.benchmark_costos         # costo real baseline vs optimizado
```

GitHub Actions (`.github/workflows/ci.yml`) corre en cada push y PR: pytest → bandit, pip-audit y gitleaks →
build de la imagen → contenedor endurecido (`--read-only`, `--cap-drop ALL`, usuario no root) → prueba de humo
(`/health`, `/ready`, `/openapi.json`, 401 sin llave, `POST /v1/criterios`) → publicación en GHCR.
