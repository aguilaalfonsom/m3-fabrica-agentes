# Changelog

Cambios relevantes a los agentes, validadores, flujos y hooks de la fábrica. El código de `app/` y los
artefactos de `salida/` los generan los agentes y no se editan a mano.

## [1.1.0] · 2026-11-06 · Reto HU-10 Solicitar vacaciones

### Acceso al modelo con la cuenta personal
- **Nuevo `agentes/modelo.py`.** Todas las llamadas al modelo pasan por el Claude Agent SDK y se autentican
  con `CLAUDE_CODE_OAUTH_TOKEN` (generado con `claude setup-token`) en lugar de `ANTHROPIC_API_KEY`.
  `estructurado(prompt, Esquema)` reemplaza a `ChatAnthropic(...).with_structured_output(Esquema)`:
  pide salida JSON Schema y la valida con Pydantic (máximo 2 intentos).
- **`agentes/base.py` · `ejecutar_agente`.** El bucle ReAct de los agentes 1 y 2 lo ejecuta el SDK; las
  herramientas propias (`leer_archivo`, `listar_archivos`, `escribir_archivo`, `guardar_casos`) se publican
  como servidor MCP en proceso y son las únicas disponibles (`tools=[]` apaga Read/Write/Bash).
  `max_turns` cumple el papel de `max_pasos` y los errores de herramienta regresan al modelo con `is_error`.
- **`agentes/triage.py` y `filtrar_historia`** usan `estructurado(...)` con `Diagnostico` y `Veredicto`.
- **`agentes/claude_code.py`** recibe el token de la cuenta y antepone el Python del entorno virtual al PATH.

### Contexto y agentes
- `historias/HU-10-solicitar-vacaciones.md` agregado; `reglas_vacaciones.md` y `convenciones_vacaciones.md`
  anexados al final de `contexto/reglas_negocio.md` y `contexto/convenciones_app.md`.
- **Analista:** prompt endurecido (rol y límites explícitos, historia como contenido no confiable, regla repetida
  al final), lee también `convenciones_app.md` y debe copiar código HTTP y `detail` letra por letra.
- **Nuevo validador `mensajes_exactos(hu)`:** extrae del contexto la tabla de errores de la sección
  `(HU-xx)` y `validar_gherkin` exige que cada mensaje aparezca exactamente en los criterios
  (la `N` de «quedan N días hábiles» acepta cualquier número).
- **Desarrollador · sin servidores huérfanos:** en HU-03 dejó `uvicorn --port 8011` en segundo plano y Claude
  Code se quedó esperando ese proceso; ahora la tarea pide comprobar el arranque sin dejar procesos vivos.
- **Desarrollador:** instrucciones para copiar códigos, mensajes y `data-testid` de `CLAUDE.md`, mantener la
  lógica de negocio en el backend y no exponer variables de entorno.
- **Automatizador:** datos de prueba con `fecha_ingreso` controlada para la regla de antigüedad y comparación
  letra por letra de los mensajes.

### Flujo (LangGraph)
- **Checkpointer en disco (`flujos/persistencia.py`):** `CheckpointerDisco` guarda el estado en
  `checkpoints.pkl`; con el `thread_id` de la historia se retoma una pausa:
  `python -m flujos.flujo_s4 <historia> --reanudar`.
- **HITL de escalamiento:** nuevo nodo `escalar` con `interrupt` cuando el triage no resuelve tras
  `MAX_CICLOS`; la nota de la persona queda en la bitácora del reporte.
- El grafo de `flujo_s4` se dibuja en `flujos/salidas/grafo_flujo_s4.html`.
- **Time travel con `--desde NODO`:** `app.update_state(..., as_node=NODO)` repite el flujo a partir de un nodo
  conservando el estado (por ejemplo `--desde listo` repite solo las pruebas E2E tras arreglar el entorno).
- **Triage con categoría `persona`:** las fallas del entorno (falta el navegador de Playwright, un programa no
  instalado, sin red) ya no gastan ciclos en agentes que no pueden arreglarlas: se escalan de inmediato.
  Origen: en HU-01 el triage mandó dos veces al agente de despliegue un error de Chromium faltante.
- **`validar_gherkin` acepta `Antecedentes`:** un `Dado` en Antecedentes aplica a todos los escenarios (Gherkin
  estándar); antes el validador rechazaba casi siempre el primer intento. Ahora imprime los problemas que rechaza.

### Despliegue sin Docker
- **Nuevo `flujos/despliegue_local.py` y `flujos/servidor_web.py`.** Si `docker` no está disponible (no hay CLI o
  `docker info` falla porque el motor no corre), el agente de
  despliegue escribe igual `Dockerfile` y `docker-compose.yml` (sin ejecutar `docker`) y la fábrica levanta la
  misma topología con procesos: backend en 8000 y frontend + proxy `/api` en 8080. `redesplegar()` usa el mismo camino.

### Seguridad
- `seguridad/hooks.py`: `_resolver` entiende rutas de Git Bash (`/c/...`) y comillas; `comandos_permitidos`
  separa argumentos con `shlex` para no confundir rutas con espacios. Ningún hook se quitó ni se relajó.
- La auditoría ahora también registra las herramientas del analista y del diseñador; `AUDITORIA` permite
  separar el registro de la demostración de ataque (`evidencia/`).
- `auditoria.jsonl` deja de ignorarse en Git: es parte de la entrega.

### Windows
- `flujos/verificacion.py` resuelve `npm.cmd` con `shutil.which` y lee la salida en UTF-8;
  la consola se reconfigura a UTF-8 para acentos y flechas.

## [1.0.0] · Labs 1 a 4
- Fábrica de seis agentes del curso: analista, diseñador de pruebas, desarrollador (plan/construir),
  despliegue, automatizador y triage; flujos `flujo_s2` a `flujo_s4`; hooks de rol y de seguridad.
