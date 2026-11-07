"""Sesión 3 · Agente 4, despliegue: componentes -> contenedores corriendo con Docker Compose.

Uso:  python -m agentes.despliegue
"""
from agentes.base import APP
from flujos.despliegue_local import hay_docker
from agentes.claude_code import EDICION, ejecutar_claude_code

INSTRUCCIONES = """Eres el ingeniero de despliegue del equipo. Empaquetas la aplicación en contenedores
y la levantas con Docker Compose. No modificas el código de la aplicación."""

ESCRITURA = ["docker-compose.yml", "backend/Dockerfile", "backend/.dockerignore",
             "frontend/Dockerfile", "frontend/.dockerignore", "frontend/nginx.conf"]
PROGRAMAS = {"cd", "ls", "cat", "docker", "curl", "sleep"}

TAREA = """Despliega la aplicación de esta carpeta:
1. backend/Dockerfile: python:3.12-slim, instala backend/requirements.txt y ejecuta
   `uvicorn main:app --host 0.0.0.0 --port 8000`.
2. frontend/Dockerfile en dos etapas: node:22 para `npm ci && npm run build`, y nginx:alpine para servir dist/.
   frontend/nginx.conf: escucha en el puerto 80 y redirige /api/ a http://backend:8000.
3. docker-compose.yml con los servicios `backend` (puerto 8000:8000, volumen ./backend/datos:/app/datos
   y healthcheck a /api/salud) y `frontend` (puerto 8080:80, depende de backend).
4. Ejecuta `docker compose up -d --build` y espera a que http://localhost:8000/api/salud y
   http://localhost:8080 respondan. Si algo falla, revisa `docker compose logs` y corrige.
Responde con las URL de la aplicación y de la documentación de la API."""

PASO_SIN_DOCKER = """4. En esta máquina NO hay Docker: no ejecutes `docker`. Revisa con `cat` que los tres archivos sean
   coherentes entre sí (rutas, puertos 8000/8080, healthcheck y proxy de /api/). La fábrica levantará
   la misma topología con procesos locales y verificará los puertos 8000 y 8080."""


def desplegar(errores: str = "") -> tuple[str, float]:
    tarea, programas = TAREA, PROGRAMAS
    if not hay_docker():                       # sin Docker: escribe los archivos pero no los ejecuta
        tarea = TAREA.split("4. Ejecuta")[0] + PASO_SIN_DOCKER + "\nResponde con un resumen de los archivos."
        programas = PROGRAMAS - {"docker"}
    prompt = tarea + (f"\n\nEl despliegue anterior falló; corrige esto:\n{errores}" if errores else "")
    return ejecutar_claude_code(prompt, agente="despliegue", cwd=APP, herramientas=EDICION,
                                escritura=ESCRITURA, programas=programas, instrucciones=INSTRUCCIONES)


if __name__ == "__main__":
    print(desplegar()[0])
