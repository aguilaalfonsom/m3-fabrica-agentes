# API de producción de la fábrica de agentes (Reto M4).
# Build:  docker build -t fabrica-agentes-api .
# Run:    docker compose up -d   (ver docker-compose.yml)
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DIR_DATOS=/datos \
    HOME=/tmp

WORKDIR /app

# Dependencias primero (capa cacheable); la rueda Linux del Agent SDK ya incluye el CLI de Claude Code
COPY produccion/requirements.txt produccion/requirements.txt
RUN pip install -r produccion/requirements.txt

# Solo lo que la API necesita: sin app/, salida/, historias de prueba ni .env
COPY agentes/ agentes/
COPY contexto/ contexto/
COPY seguridad/__init__.py seguridad/hooks.py seguridad/
COPY produccion/ produccion/
RUN rm -rf produccion/tests produccion/datos

# Mínimo privilegio: usuario sin privilegios y sin shell de login; solo /datos es escribible
RUN groupadd --system fabrica && useradd --system --gid fabrica --no-create-home --shell /usr/sbin/nologin fabrica \
    && mkdir -p /datos && chown fabrica:fabrica /datos
USER fabrica

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

CMD ["uvicorn", "produccion.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers"]
