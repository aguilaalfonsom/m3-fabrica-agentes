"""Sustituto local de nginx (puerto 8080): sirve app/frontend/dist y redirige /api/ al backend.

Replica frontend/nginx.conf para que las pruebas E2E usen la misma URL que con Docker.
"""
import os
from pathlib import Path

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse

DIST = Path(__file__).resolve().parent.parent / "app" / "frontend" / "dist"
BACKEND = os.environ.get("URL_BACKEND", "http://127.0.0.1:8000")
SIN_REENVIO = {"host", "content-length", "transfer-encoding", "connection", "content-encoding"}

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
cliente = httpx.AsyncClient(base_url=BACKEND, timeout=30)


@app.api_route("/api/{ruta:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def api(ruta: str, request: Request) -> Response:
    r = await cliente.request(request.method, f"/api/{ruta}", params=request.query_params,
                              content=await request.body(),
                              headers={k: v for k, v in request.headers.items() if k.lower() not in SIN_REENVIO})
    return Response(r.content, status_code=r.status_code,
                    headers={k: v for k, v in r.headers.items() if k.lower() not in SIN_REENVIO})


@app.get("/{ruta:path}")
async def estatico(ruta: str) -> FileResponse:
    archivo = (DIST / ruta).resolve()
    if ruta and archivo.is_file() and archivo.is_relative_to(DIST):
        return FileResponse(archivo)
    return FileResponse(DIST / "index.html")          # la SPA resuelve sus propias rutas
