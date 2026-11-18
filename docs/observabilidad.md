# Observabilidad

Tres señales unidas por **un mismo ID**: cada petición recibe (o respeta) `X-Request-ID`. Ese valor aparece en
la respuesta, en cada línea de log, en la auditoría y en los metadatos de la traza de LangSmith.

## 1. Trazas con LangSmith

- **Activación**: `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT=m4-fabrica-produccion` (en `.env`).
- **Qué se traza**: el grafo completo (`criterios`) y cada nodo (`preparar`, `filtrar`, `analizar`,
  `validar_criterios`, `disenar`, `validar_casos`, `validar_salida`) como spans; cada llamada al modelo como run
  `llm:<agente>` con:
  - `ls_model_name` (Haiku o Sonnet), tokens de entrada, salida y caché (`usage_metadata`), **costo en USD**;
  - el prompt que vio el modelo (ya sin PII) y la salida estructurada;
  - etiquetas `agente:<nombre>`, `modelo:<id>` y, en la raíz, metadatos `request_id`, `cliente` (hash de la llave) y estrategias activas.
- **Ejemplo real** (HU-10, `request_id=166ed2fb…`): la raíz suma 43,592 tokens y $0.1103; los hijos muestran
  `filtrar` (Haiku, 2,497 tokens, $0.0006), `analizar` (Sonnet, 14,115 tokens, $0.0991) y `disenar` (Haiku,
  26,980 tokens, $0.0107).
- **Depurar en producción**: con el `X-Request-ID` que reporta un cliente, filtra en LangSmith por metadata
  `request_id` y ve qué nodo falló, con qué prompt y cuántos intentos hubo. Las corridas del benchmark llevan
  etiquetas `benchmark:baseline` / `benchmark:optimizado` para compararlas lado a lado.

## 2. Logs estructurados (JSON)

Una línea JSON por evento, a stdout (lo recoge Docker o cualquier agregador):

```json
{"ts": "2026-11-18T15:56:26Z", "nivel": "INFO", "logger": "fabrica", "request_id": "166ed2fbe773443285e13983930abe9e",
 "mensaje": "petición", "metodo": "POST", "ruta": "/v1/criterios", "estado": 200, "latencia_ms": 102657.7,
 "cliente": "0b086f566fdebbe3"}
```

- Campos fijos: `ts`, `nivel`, `request_id`, `mensaje`; contexto adicional por evento.
- `cliente` es una huella (hash) de la API key, nunca la llave.
- Un filtro enmascara `sk-ant-…`, `lsv2_…` y `Bearer …` aunque alguien los registre por error.
- Nivel por `NIVEL_LOG`; librerías ruidosas en WARNING.

## 3. Métricas (latencia, errores y costos por petición)

| Endpoint | Formato | Uso |
|---|---|---|
| `GET /metrics` | Prometheus (texto) | Scraping por Prometheus/Grafana |
| `GET /v1/metricas` | JSON | Panel, scripts y video |
| `GET /dashboard` | HTML | Panel de operación (se actualiza cada 3 s) |

Series principales:

| Serie | Tipo | Significado |
|---|---|---|
| `fabrica_peticiones_total{ruta,estado}` | counter | Tráfico y errores (4xx/5xx) por ruta |
| `fabrica_latencia_ms_bucket{ruta,le}` | histogram | Latencia; el JSON trae p50/p95/promedio |
| `fabrica_costo_usd_total{modelo}` | counter | Costo acumulado por modelo |
| `fabrica_tokens_total{modelo,tipo}` | counter | Tokens de entrada, salida y lectura de caché |
| `fabrica_llamadas_llm_total{agente,modelo}` | counter | Evidencia del ruteo (qué agente usó qué modelo) |
| `fabrica_cache_total{resultado}` y `fabrica_ahorro_cache_usd_total` | counter | Aciertos de caché y dinero ahorrado |
| `fabrica_bloqueos_total{motivo}` | counter | Seguridad: sin llave, sin permiso, límite, guardrail, entrada inválida, capacidad |
| `fabrica_pii_detectada_total{tipo}` | counter | PII enmascarada en entrada y salida |
| `fabrica_peticiones_en_curso` | gauge | Concurrencia actual |

Además, **cada respuesta** de `/v1/criterios` trae su propio `costo_usd`, `latencia_ms` y el desglose por agente
(modelo, tokens, costo, latencia, intentos): métrica de negocio por petición.

## 4. Panel de operación

`/dashboard` (pide una llave de rol `lector` o `cliente`): peticiones, latencia p50/p95, errores 5xx, costo,
ahorro por caché, tasa de aciertos, peticiones en curso, bloqueos de seguridad, costo por modelo, llamadas por
agente y modelo, respuestas por estado y eventos de seguridad.

## Runbook rápido

| Síntoma | Dónde mirar | Acción |
|---|---|---|
| Latencia p95 alta | panel / `fabrica_latencia_ms` + LangSmith (nodo lento) | Revisar si el analista hace reintentos (`intentos`), subir `MAX_CONCURRENCIA` si hay cola |
| 429 frecuentes | `fabrica_bloqueos_total{motivo}` | `limite_peticiones` → cliente abusivo; `capacidad` → escalar |
| 502 | auditoría `criterios_invalidos` + traza | El validador rechazó 2 veces: ver `problemas` en la traza |
| Costo sube | `fabrica_costo_usd_total{modelo}` + `llamadas_llm` | ¿La cascada escala a Sonnet seguido? ¿La caché está activa? |
| `/ready` en 503 | cuerpo de `/ready` | Falta credencial, volumen no escribible o llaves |
