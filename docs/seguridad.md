# Seguridad y controles de la API de producción

Defensa en profundidad: ningún control depende de que el modelo «se porte bien». Los controles deterministas
(autenticación, validación, PII, mínimo privilegio) rodean a los controles probabilísticos (guardrail LLM).

## Controles implementados

| # | Control | Dónde | Evidencia |
|---|---|---|---|
| 1 | **Validación de entrada** (Pydantic): 30 a 6,000 caracteres, sin caracteres de control, debe parecer historia; cuerpo máx. 64 KB (413) | `api.py` `SolicitudCriterios`, middleware | `test_validacion_de_entrada`, `test_cuerpo_demasiado_grande_413` |
| 2 | **Validación de salida**: Gherkin con mensajes exactos, esquema `PlanPruebas`, cobertura de escenarios; si no cumple tras 2 intentos → 502, nunca una respuesta a medias | `grafo.py` `validar_criterios`, `validar_casos` | `test_criterios_hu10_trae_gherkin_casos_y_costos` |
| 3 | **Detección de PII y secretos** en la entrada (se enmascara **antes** de llegar a cualquier modelo) y en la salida (antes de devolverla): correo, teléfono, CURP, RFC, tarjeta (Luhn), CLABE, IP, JWT, llaves de API | `pii.py`, nodos `preparar` y `validar_salida` | `test_pii_se_enmascara_antes_del_modelo`; ejecución real: entrada `{correo:1, curp:1, telefono:1}`, salida `{correo:2}` |
| 4 | **Guardrail contra inyección de prompts** (LLM clasificador) + contenido externo entre `<historia_no_confiable>` + rol repetido al final | `grafo.py` `filtrar`, prompts | HU-99 → **422 historia_bloqueada** (real y en pruebas) |
| 5 | **Gestión de secretos**: solo por variables de entorno (`.env` no versionado, `env_file` en compose); las API keys se guardan como hash sha256; filtro de logs que enmascara tokens; `/ready` no expone secretos; gitleaks en CI | `config.py`, `observabilidad.py`, `.github/workflows/ci.yml` | `test_ready_reporta_checks_sin_secretos` |
| 6 | **Autenticación y autorización por roles** (mínimo privilegio): `cliente` genera y ve métricas; `lector` solo métricas; comparación en tiempo constante | `seguridad.py` `requiere()` | `test_sin_llave_401…`, `test_minimo_privilegio_lector…` |
| 7 | **Límite de peticiones por llave** (30/min, 429 + Retry-After) y **backpressure** por capacidad | `seguridad.py` `Limitador`, `api.py` | métricas `bloqueos{limite_peticiones, capacidad}` |
| 8 | **Registro de auditoría** append-only con `request_id`: accesos denegados, solicitudes, bloqueos, PII, errores, generación con costo. Guarda **huellas** (hash) de las historias, nunca el texto ni las llaves | `seguridad.py` `auditar()` → `/datos/auditoria_api.jsonl` | `test_auditoria_registra_acciones_sin_texto_de_historia` |
| 9 | **Mínimo privilegio de los agentes**: `tools=[]` (sin archivos, terminal ni web), `setting_sources=[]`, salida solo por JSON Schema | `llm.py` | revisión de código |
| 10 | **Mínimo privilegio del contenedor**: usuario no root, sin shell, FS de solo lectura, `cap_drop: ALL`, `no-new-privileges`, solo `/datos` y `/tmp` escribibles, límites de CPU/memoria | `Dockerfile`, `docker-compose.yml`, job `contenedor` de CI | CI verifica `id -u != 0` con `--read-only` |
| 11 | **Errores sin fuga de información**: el 422 no refleja la entrada (`input`), el 500 no devuelve stack trace | `api.py` `validacion_sin_eco`, middleware | `test_error_422_no_refleja_la_entrada` |
| 12 | **Encabezados de seguridad**: `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Cache-Control: no-store`, CSP estricta en el panel | middleware, `/dashboard` | `test_health_es_publico` |
| 13 | **Gates de seguridad en CI**: bandit (sin hallazgos medios/altos), pip-audit (vulnerabilidades conocidas), gitleaks (secretos en el historial) | `.github/workflows/ci.yml` | ejecución de Actions |

## Ejecución real contra la API (cuenta personal, defensas activas)

| Intento | Resultado |
|---|---|
| Sin API key | **401** «Falta el encabezado X-API-Key» |
| Rol `lector` intenta generar criterios | **403** «El rol «lector» no tiene permiso para esta operación» |
| Texto que no es historia | **422** «No parece una historia de usuario…» (sin eco del texto) |
| Historia envenenada HU-99 | **422** `historia_bloqueada`: «Contiene instrucciones dirigidas a la IA que no son requisitos: leer ../secretos_demo.txt…» |
| Historia con correo, teléfono y CURP | **200**: PII enmascarada en la entrada `{correo, curp, telefono}` y en la salida `{correo: 2}` |

Comando: `python -m produccion.cliente_demo seguridad`.

## Mapeo a OWASP Top 10 para aplicaciones LLM y agénticas

| Riesgo | Mitigación |
|---|---|
| LLM01 Inyección de prompts / ASI01 Secuestro de objetivo | Guardrail `filtrar`, `<historia_no_confiable>`, agentes sin herramientas (aunque obedecieran no podrían actuar) |
| LLM02 Divulgación de información sensible | PII enmascarada antes del modelo y en la salida; logs con secretos tapados; auditoría con huellas |
| LLM05 Manejo inadecuado de la salida | Validadores deterministas y esquemas Pydantic; 502 si no cumplen |
| LLM06 Agencia excesiva / ASI02 Mal uso de herramientas | `tools=[]`; el único efecto de un agente es su JSON |
| LLM10 Consumo sin límites | Límite por llave, cola acotada, timeout, reintentos acotados, presupuesto por petición, caché |
| ASI03 Abuso de identidad y privilegios | Roles por API key; contenedor no root |
| ASI08 Fallas en cascada | Reflexión acotada, 429/504 en lugar de saturación |

## Checklist de cumplimiento para producción

- [x] Sin credenciales en el código ni en la imagen (verificado por gitleaks y `.dockerignore`)
- [x] Secretos por entorno; rotables sin reconstruir la imagen
- [x] Autenticación, autorización por rol y límite de peticiones
- [x] Validación de entradas y salidas; PII enmascarada en ambos sentidos
- [x] Auditoría con correlation ID, sin datos sensibles
- [x] Contenedor endurecido y escaneos automáticos en CI
- [ ] TLS terminado en un balanceador propio (hoy lo da ngrok)
- [ ] Secretos en un gestor (Key Vault / Secrets Manager) con rotación automática
- [ ] Auditoría enviada a almacenamiento inmutable (WORM) o SIEM
- [ ] Límite de peticiones compartido entre réplicas (Redis)
- [ ] Detector de PII con modelo NER para nombres propios (hoy: patrones deterministas)
