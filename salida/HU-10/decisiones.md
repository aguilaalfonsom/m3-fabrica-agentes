# Decisiones · HU-10 Solicitar vacaciones

Resultado: **LISTA** en una sola pasada. 35 escenarios Gherkin, 35 casos de prueba, 0 ciclos de corrección,
129 pruebas pasadas (pytest + Playwright, 4 omitidas) y 1.06 USD de agentes. La historia corrió después de
HU-01 a HU-03, sobre la app que ya existía (`salida/HU-10/reporte.md`).

## 1. Qué pasos son workflow y cuáles son agente

| Paso | Tipo | Por qué |
| --- | --- | --- |
| `filtrar_historia` | LLM de una llamada con salida Pydantic | Clasificar sí/no no necesita herramientas ni bucle |
| Analista → `criterios.feature` | **Agente** (bucle ReAct con `leer_archivo`/`escribir_archivo`) | Decide qué leer del contexto y cuántos escenarios escribir |
| Diseñador → `casos_prueba.json` | **Agente** | Igual que el analista, con salida validada por Pydantic |
| Plan del desarrollador | **Agente** de solo lectura (Claude Code) | Explora el código existente antes de proponer |
| Aprobación del plan, preguntas abiertas, escalamiento | **Workflow** + `interrupt` (HITL) | La decisión es de una persona, no del modelo |
| Construcción | **Agente** (Claude Code con hooks de rol) | Edita varios archivos y comprueba su trabajo |
| Verificación, despliegue local, pytest/Playwright | **Workflow** determinista | El código decide si se cumplió, no el agente |
| Despliegue y automatizador | **Agentes** en paralelo (fan-out), con `listo` como fan-in | No dependen uno del otro |
| Triage | LLM de una llamada que **solo enruta** (`Literal` cerrado) | Supervisor: no corrige nada |

El grafo `flujo_s4` (`flujos/salidas/grafo_flujo_s4.html`) fija el orden y los ciclos. Los agentes solo deciden
dentro de su nodo.

## 2. Cómo se validó cada salida

- **Criterios:** `validar_gherkin` revisa `# language: es`, `Característica`, al menos 2 escenarios y
  Dado/Cuando/Entonces. Además `mensajes_exactos('HU-10')` extrae la tabla de errores de
  `convenciones_app.md` y exige los **8 `detail` letra por letra** (la N de «quedan N días» acepta cualquier número).
  En HU-10 lo aceptó al primer intento; en HU-03 el primer intento se rechazó («El escenario 14 no tiene
  'Cuando'») y el reintento lo corrigió.
- **Casos:** modelo Pydantic al guardar con `guardar_casos`.
- **Plan:** lo revisé contra el contexto antes de aprobarlo: códigos 404/409/400, los mensajes, el texto de éxito
  y los 6 `data-testid`.
- **Código:** salud de la API y `npm run build`. Después comprobé por mi cuenta que los 8 mensajes y los 6
  `data-testid` existen en `app/`, y que `contar_dias_habiles` da 8, 4 y 0 en los ejemplos de las reglas.
- **App completa:** 129 pruebas E2E. Las 3 preguntas abiertas del analista (traslapes, GET de un empleado
  inexistente, 29 de febrero) se aceptaron como decisiones documentadas en el plan.

## 3. Qué corregí en los agentes (no en su salida)

Ninguno de estos cambios toca `app/` ni `salida/`; todos están en `CHANGELOG.md`.

1. **Acceso con la cuenta personal:** todas las llamadas pasan por el Agent SDK con `CLAUDE_CODE_OAUTH_TOKEN`
   (`agentes/modelo.py`).
2. **Analista:** prompt endurecido con historia no confiable, y validador de mensajes exactos, porque en las
   primeras pruebas copiaba mensajes parafraseados.
3. **Validador:** aceptaba mal los `Antecedentes` y rechazaba casi siempre el primer intento. Ahora acepta el
   `Dado` heredado e imprime lo que rechaza.
4. **Triage → `persona`:** en HU-01 faltaba Chromium y el triage gastó 2 ciclos enviándolo al agente de
   despliegue. Ahora las fallas de entorno se escalan de inmediato. Después resolví el entorno y repetí solo las
   pruebas con `--desde listo` (time travel).
5. **Desarrollador:** en HU-03 dejó `uvicorn --port 8011` vivo y Claude Code se quedó esperando. Ahora la tarea
   pide comprobar el arranque sin dejar procesos; en HU-10 ya no ocurrió.
6. **Despliegue sin Docker:** el CLI existe, pero el motor no corre (Windows ARM sin WSL). `hay_docker()` exige que
   `docker info` responda y, si no, la fábrica levanta la misma topología con procesos (8000/8080).
7. **Checkpointer en disco:** permite reanudar una pausa (`--reanudar`) en lugar de repetir todo y pagar de nuevo.

## 4. Seguridad aplicada a esta historia

El filtro dio **OK** para HU-10 y **BLOQUEADA** para HU-99. En la auditoría de HU-10 (`auditoria.jsonl`) hay
60 llamadas a herramientas y **0** `deny`: ningún agente intentó salir de su carpeta. La demostración completa
del ataque está en `salida/seguridad.md`.

## 5. Qué haría distinto

- Generar los criterios con IDs de regla para trazar regla → escenario → caso → prueba.
- Convertir las preguntas abiertas recurrentes (traslapes, mensajes de éxito) en reglas del contexto.
- Medir el costo por nodo para fijar un presupuesto por historia, no solo por llamada.
