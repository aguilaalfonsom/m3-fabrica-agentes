# language: es
Característica: Solicitar vacaciones (HU-10)
  Como empleado de la empresa
  quiero solicitar días de vacaciones indicando fecha de inicio y de fin
  para que mi solicitud quede registrada y sepa cuántos días me quedan en el año

  Antecedentes:
    Dado un empleado activo con id 7 y fecha_ingreso "2024-03-10"
    Y que no tiene solicitudes de vacaciones registradas

  # ---------- Camino feliz ----------

  Escenario: Solicitud válida por API descuenta solo días hábiles
    Cuando hace POST /api/empleados/7/vacaciones con fecha_inicio "2026-07-06" y fecha_fin "2026-07-10"
    Entonces la respuesta es 201
    Y el cuerpo contiene empleado_id 7, fecha_inicio "2026-07-06", fecha_fin "2026-07-10", dias_habiles 5 y dias_restantes 7

  Escenario: Solicitud válida desde la pantalla muestra el mensaje de éxito
    Dado que abre el formulario con el botón "vacaciones-abrir-7"
    Y que "vacaciones-disponibles" muestra 12
    Cuando escribe "2026-07-06" en "vacaciones-fecha-inicio" y "2026-07-10" en "vacaciones-fecha-fin"
    Y pulsa "vacaciones-enviar"
    Entonces "vacaciones-mensaje" muestra "Solicitud registrada: 5 días hábiles. Te quedan 7 días hábiles en 2026."
    Y "vacaciones-disponibles" muestra 7

  Escenario: Consultar el saldo del año tras una solicitud
    Dado que el empleado 7 tiene registrada la solicitud del "2026-12-21" al "2026-12-31"
    Cuando hace GET /api/empleados/7/vacaciones?anio=2026
    Entonces la respuesta es 200
    Y dias_usados es 8 y dias_disponibles es 4
    Y solicitudes contiene un elemento con fecha_inicio "2026-12-21", fecha_fin "2026-12-31" y dias_habiles 8

  Escenario: Saldo de un año sin solicitudes
    Cuando hace GET /api/empleados/7/vacaciones?anio=2027
    Entonces la respuesta es 200
    Y dias_usados es 0, dias_disponibles es 12 y solicitudes está vacía

  # ---------- Regla 3: días hábiles ----------

  Escenario: Un día festivo dentro del periodo no se descuenta
    Cuando hace POST /api/empleados/7/vacaciones con fecha_inicio "2026-09-14" y fecha_fin "2026-09-18"
    Entonces la respuesta es 201
    Y dias_habiles es 4 y dias_restantes es 8

  Escenario: Fines de semana y Navidad no se descuentan
    Cuando hace POST /api/empleados/7/vacaciones con fecha_inicio "2026-12-21" y fecha_fin "2026-12-31"
    Entonces la respuesta es 201
    Y dias_habiles es 8 y dias_restantes es 4

  Escenario: Un festivo de 2027 también se excluye
    Cuando hace POST /api/empleados/7/vacaciones con fecha_inicio "2027-09-13" y fecha_fin "2027-09-17"
    Entonces la respuesta es 201
    Y dias_habiles es 4 y dias_restantes es 8

  Escenario: Un solo día hábil cuenta como 1 día
    Cuando hace POST /api/empleados/7/vacaciones con fecha_inicio "2026-07-06" y fecha_fin "2026-07-06"
    Entonces la respuesta es 201
    Y dias_habiles es 1 y dias_restantes es 11

  Escenario: Periodo de sábado y domingo se rechaza
    Cuando hace POST /api/empleados/7/vacaciones con fecha_inicio "2026-07-11" y fecha_fin "2026-07-12"
    Entonces la respuesta es 400
    Y el detail es "El periodo no incluye días hábiles"

  Escenario: Periodo formado solo por un festivo en sábado y un domingo se rechaza
    Cuando hace POST /api/empleados/7/vacaciones con fecha_inicio "2027-05-01" y fecha_fin "2027-05-02"
    Entonces la respuesta es 400
    Y el detail es "El periodo no incluye días hábiles"

  Escenario: Periodo de un solo día festivo se rechaza
    Cuando hace POST /api/empleados/7/vacaciones con fecha_inicio "2026-09-16" y fecha_fin "2026-09-16"
    Entonces la respuesta es 400
    Y el detail es "El periodo no incluye días hábiles"

  # ---------- Regla 1: antigüedad ----------

  Escenario: Cumple exactamente un año de antigüedad el día de inicio
    Dado un empleado activo con id 8 y fecha_ingreso "2025-12-21"
    Cuando hace POST /api/empleados/8/vacaciones con fecha_inicio "2026-12-21" y fecha_fin "2026-12-31"
    Entonces la respuesta es 201
    Y dias_habiles es 8 y dias_restantes es 4

  Escenario: Le faltan días para cumplir un año
    Dado un empleado activo con id 8 y fecha_ingreso "2025-12-21"
    Cuando hace POST /api/empleados/8/vacaciones con fecha_inicio "2026-12-18" y fecha_fin "2026-12-18"
    Entonces la respuesta es 400
    Y el detail es "Se requiere al menos un año de antigüedad a la fecha de inicio"

  Escenario: Falta un solo día para cumplir un año
    Dado un empleado activo con id 8 y fecha_ingreso "2025-12-21"
    Cuando hace POST /api/empleados/8/vacaciones con fecha_inicio "2026-12-20" y fecha_fin "2026-12-22"
    Entonces la respuesta es 400
    Y el detail es "Se requiere al menos un año de antigüedad a la fecha de inicio"

  Escenario: La antigüedad se valida antes que los días hábiles
    Dado un empleado activo con id 8 y fecha_ingreso "2025-12-21"
    Cuando hace POST /api/empleados/8/vacaciones con fecha_inicio "2026-07-11" y fecha_fin "2026-07-12"
    Entonces la respuesta es 400
    Y el detail es "Se requiere al menos un año de antigüedad a la fecha de inicio"

  # ---------- Regla 2: tope anual ----------

  Escenario: Usar exactamente los días que quedan
    Dado que el empleado 7 ya usó 5 días hábiles en 2026
    Cuando hace POST /api/empleados/7/vacaciones con fecha_inicio "2026-07-13" y fecha_fin "2026-07-21"
    Entonces la respuesta es 201
    Y dias_habiles es 7 y dias_restantes es 0

  Escenario: Pedir un día más de los que quedan
    Dado que el empleado 7 ya usó 11 días hábiles en 2026
    Cuando hace POST /api/empleados/7/vacaciones con fecha_inicio "2026-07-06" y fecha_fin "2026-07-07"
    Entonces la respuesta es 400
    Y el detail es "La solicitud excede los días disponibles: quedan 1 días hábiles"

  Escenario: Pedir el último día disponible
    Dado que el empleado 7 ya usó 11 días hábiles en 2026
    Cuando hace POST /api/empleados/7/vacaciones con fecha_inicio "2026-07-06" y fecha_fin "2026-07-06"
    Entonces la respuesta es 201
    Y dias_habiles es 1 y dias_restantes es 0

  Escenario: Solicitud que rebasa el saldo
    Dado que el empleado 7 ya usó 4 días hábiles en 2026
    Cuando hace POST /api/empleados/7/vacaciones con fecha_inicio "2026-08-03" y fecha_fin "2026-08-13"
    Entonces la respuesta es 400
    Y el detail es "La solicitud excede los días disponibles: quedan 8 días hábiles"

  Escenario: Sin días disponibles
    Dado que el empleado 7 ya usó 12 días hábiles en 2026
    Cuando hace POST /api/empleados/7/vacaciones con fecha_inicio "2026-08-03" y fecha_fin "2026-08-03"
    Entonces la respuesta es 400
    Y el detail es "La solicitud excede los días disponibles: quedan 0 días hábiles"

  Escenario: Un periodo de más de 12 días hábiles con saldo completo se rechaza
    Cuando hace POST /api/empleados/7/vacaciones con fecha_inicio "2026-08-03" y fecha_fin "2026-08-19"
    Entonces la respuesta es 400
    Y el detail es "La solicitud excede los días disponibles: quedan 12 días hábiles"

  Escenario: El error de tope se muestra en la pantalla
    Dado que el empleado 7 ya usó 12 días hábiles en 2026
    Y que abre el formulario con el botón "vacaciones-abrir-7"
    Cuando escribe "2026-08-03" en "vacaciones-fecha-inicio" y "2026-08-03" en "vacaciones-fecha-fin"
    Y pulsa "vacaciones-enviar"
    Entonces "vacaciones-mensaje" muestra "La solicitud excede los días disponibles: quedan 0 días hábiles"
    Y "vacaciones-disponibles" muestra 0

  Escenario: Los días usados en 2026 no afectan el saldo de 2027
    Dado que el empleado 7 ya usó 12 días hábiles en 2026
    Cuando hace POST /api/empleados/7/vacaciones con fecha_inicio "2027-07-05" y fecha_fin "2027-07-09"
    Entonces la respuesta es 201
    Y dias_habiles es 5 y dias_restantes es 7

  # ---------- Validaciones de fechas, año y empleado ----------

  Escenario: Fecha de fin anterior a la de inicio
    Cuando hace POST /api/empleados/7/vacaciones con fecha_inicio "2026-07-10" y fecha_fin "2026-07-06"
    Entonces la respuesta es 400
    Y el detail es "La fecha de fin no puede ser anterior a la fecha de inicio"

  Escenario: Periodo que cruza de un año a otro
    Cuando hace POST /api/empleados/7/vacaciones con fecha_inicio "2026-12-28" y fecha_fin "2027-01-08"
    Entonces la respuesta es 400
    Y el detail es "Las vacaciones deben estar dentro de un mismo año calendario"

  Escenario: Año fuera de la tabla de festivos
    Cuando hace POST /api/empleados/7/vacaciones con fecha_inicio "2028-01-10" y fecha_fin "2028-01-14"
    Entonces la respuesta es 400
    Y el detail es "Solo se pueden solicitar vacaciones en 2026 y 2027"

  Escenario: Año anterior a la tabla de festivos
    Cuando hace POST /api/empleados/7/vacaciones con fecha_inicio "2025-12-15" y fecha_fin "2025-12-19"
    Entonces la respuesta es 400
    Y el detail es "Solo se pueden solicitar vacaciones en 2026 y 2027"

  Escenario: Empleado que no existe
    Cuando hace POST /api/empleados/9999/vacaciones con fecha_inicio "2026-07-06" y fecha_fin "2026-07-10"
    Entonces la respuesta es 404
    Y el detail es "Empleado no encontrado"

  Escenario: Empleado dado de baja
    Dado un empleado con id 10 en estado "baja"
    Cuando hace POST /api/empleados/10/vacaciones con fecha_inicio "2026-07-06" y fecha_fin "2026-07-10"
    Entonces la respuesta es 409
    Y el detail es "No se pueden solicitar vacaciones para un empleado dado de baja"

  Escenario: El empleado dado de baja se valida antes que las fechas
    Dado un empleado con id 10 en estado "baja"
    Cuando hace POST /api/empleados/10/vacaciones con fecha_inicio "2026-07-10" y fecha_fin "2026-07-06"
    Entonces la respuesta es 409
    Y el detail es "No se pueden solicitar vacaciones para un empleado dado de baja"

  Escenario: Formato de fecha inválido
    Cuando hace POST /api/empleados/7/vacaciones con fecha_inicio "10/07/2026" y fecha_fin "2026-07-12"
    Entonces la respuesta es 422

  Escenario: Una solicitud rechazada no descuenta días
    Dado que el empleado 7 ya usó 4 días hábiles en 2026
    Y que la solicitud del "2026-08-03" al "2026-08-13" fue rechazada por exceder el saldo
    Cuando hace GET /api/empleados/7/vacaciones?anio=2026
    Entonces dias_usados es 4 y dias_disponibles es 8

  # ---------- Pantalla ----------

  Escenario: El botón de vacaciones aparece en empleados activos
    Cuando abre el directorio de empleados
    Entonces existe el elemento "vacaciones-abrir-7"

  Escenario: Un empleado dado de baja no tiene botón de vacaciones
    Dado un empleado con id 10 en estado "baja"
    Cuando abre el directorio de empleados
    Entonces no existe el elemento "vacaciones-abrir-10"

  Escenario: El error de antigüedad se muestra en la pantalla
    Dado un empleado activo con id 8 y fecha_ingreso "2025-12-21"
    Y que abre el formulario con el botón "vacaciones-abrir-8"
    Cuando escribe "2026-12-18" en "vacaciones-fecha-inicio" y "2026-12-18" en "vacaciones-fecha-fin"
    Y pulsa "vacaciones-enviar"
    Entonces "vacaciones-mensaje" muestra "Se requiere al menos un año de antigüedad a la fecha de inicio"

# Preguntas abiertas
# - ¿Se permiten solicitudes cuyos periodos se traslapen con otra ya registrada del mismo empleado? El contexto no lo define; no se escribió escenario.
# - ¿Qué responde GET /api/empleados/{id}/vacaciones para un empleado inexistente o con anio fuera de 2026-2027? El contexto solo define los errores del POST.
# - La regla del 29 de febrero (aniversario el 1 de marzo) no se puede verificar con 2026 y 2027 como únicos años permitidos, por lo que no se escribió escenario.
