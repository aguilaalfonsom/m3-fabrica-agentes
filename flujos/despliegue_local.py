"""Despliegue local, determinista, para máquinas sin Docker (por ejemplo Windows ARM sin WSL).

El agente de despliegue sigue escribiendo Dockerfile y docker-compose.yml (la entrega es portable),
pero si `docker` no existe en la máquina, este módulo levanta la misma topología con procesos:

    backend   -> uvicorn main:app en el puerto 8000 (igual que el servicio `backend`)
    frontend  -> flujos/servidor_web.py en el puerto 8080: sirve frontend/dist y redirige /api/
                 al backend (lo mismo que hace nginx.conf en el contenedor)

Uso:  python -m flujos.despliegue_local          (levanta)
      python -m flujos.despliegue_local detener
"""
import json
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

from agentes.base import APP, RAIZ

ESTADO = RAIZ / ".despliegue_local.json"
LOGS = RAIZ / "logs"


def hay_docker() -> bool:
    """Docker sirve solo si el CLI existe Y el motor responde (Docker Desktop instalado sin WSL no basta)."""
    docker = shutil.which("docker")
    if docker is None:
        return False
    try:
        return subprocess.run([docker, "info"], capture_output=True, timeout=20).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _npm(*args: str) -> tuple[bool, str]:
    r = subprocess.run([shutil.which("npm") or "npm", *args], cwd=APP / "frontend", capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=900)
    return r.returncode == 0, (r.stdout + r.stderr)[-3000:]


def _lanzar(nombre: str, comando: list[str], cwd: Path, env: dict | None = None) -> int:
    """Arranca un proceso que sobrevive al flujo (como un contenedor con `-d`)."""
    LOGS.mkdir(exist_ok=True)
    banderas = (subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS) if os.name == "nt" else 0
    salida = open(LOGS / f"{nombre}.log", "w", encoding="utf-8")
    p = subprocess.Popen(comando, cwd=cwd, stdout=salida, stderr=subprocess.STDOUT, env=env or os.environ.copy(),
                         creationflags=banderas, start_new_session=os.name != "nt")
    return p.pid


def detener() -> None:
    if not ESTADO.exists():
        return
    for pid in json.loads(ESTADO.read_text(encoding="utf-8")).values():
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
            else:
                os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
    ESTADO.unlink()


def levantar() -> tuple[bool, str]:
    """Equivalente a `docker compose up -d --build`: construye el frontend y arranca ambos servicios."""
    detener()
    if not (APP / "backend" / "main.py").exists():
        return False, "No existe app/backend/main.py"
    ok, log = _npm("install") if not (APP / "frontend" / "node_modules").exists() else (True, "")
    if ok:
        ok, log = _npm("run", "build")
    if not ok:
        return False, f"Falló el build del frontend:\n{log}"
    pids = {
        "backend": _lanzar("backend", [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1",
                                       "--port", "8000"], APP / "backend"),
        "frontend": _lanzar("frontend", [sys.executable, "-m", "uvicorn", "flujos.servidor_web:app",
                                         "--host", "127.0.0.1", "--port", "8080"], RAIZ),
    }
    ESTADO.write_text(json.dumps(pids), encoding="utf-8")
    return True, f"Procesos locales: {pids} (logs en logs/)"


if __name__ == "__main__":
    if sys.argv[1:] == ["detener"]:
        detener()
        print("Despliegue local detenido")
    else:
        print(levantar()[1])
