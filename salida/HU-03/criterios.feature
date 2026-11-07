# language: es
Característica: Editar y dar de baja a un empleado
  Como persona del área de Recursos Humanos
  quiero cambiar el puesto y el departamento de un empleado, y poder darlo de baja
  para mantener el directorio al día sin perder el historial

  Antecedentes:
    Dado que existe el empleado con id 1, número "EMP-0001", nombre "Ana Torres", correo "ana.torres@empresa.com", puesto "Analista", departamento "Ventas", fecha de ingreso "2024-03-10" y estado "activo"

  # ---------- Edición ----------

  Escenario: Cambiar puesto y departamento de un empleado activo
    Cuando edito al empleado 1 con puesto "Líder de Finanzas" y departamento "Finanzas"
    Entonces la API responde 200
    Y el empleado 1 tiene puesto "Líder de Finanzas" y departamento "Finanzas"
    Y la pantalla muestra en "mensaje-exito" que el cambio se guardó
    Y la fila "fila-empleado-1" del directorio muestra el puesto y departamento nuevos

  Escenario: El número de empleado y el correo no cambian al editar
    Cuando edito al empleado 1 con puesto "Líder de Finanzas" y departamento "Finanzas"
    Entonces el empleado 1 conserva el número "EMP-0001"
    Y el empleado 1 conserva el correo "ana.torres@empresa.com"
    Y el empleado 1 conserva el nombre "Ana Torres" y la fecha de ingreso "2024-03-10"

  Escenario: Puesto con el mínimo permitido de 2 caracteres
    Cuando edito al empleado 1 con puesto "QA" y departamento "Tecnología"
    Entonces la API responde 200
    Y el empleado 1 tiene puesto "QA"

  Escenario: Puesto con el máximo permitido de 60 caracteres
    Cuando edito al empleado 1 con un puesto de exactamente 60 caracteres y departamento "Operaciones"
    Entonces la API responde 200
    Y el empleado 1 tiene ese puesto de 60 caracteres

  Escenario: Puesto de 1 carácter es rechazado
    Cuando edito al empleado 1 con puesto "Q" y departamento "Tecnología"
    Entonces la API responde 422
    Y la pantalla indica que se debe corregir el campo "puesto"
    Y el empleado 1 conserva el puesto "Analista"

  Escenario: Puesto de 61 caracteres es rechazado
    Cuando edito al empleado 1 con un puesto de exactamente 61 caracteres y departamento "Tecnología"
    Entonces la API responde 422
    Y la pantalla indica que se debe corregir el campo "puesto"
    Y el empleado 1 conserva el puesto "Analista"

  Escenario: Puesto vacío es rechazado
    Cuando edito al empleado 1 con puesto "" y departamento "Tecnología"
    Entonces la API responde 422
    Y la pantalla indica que se debe corregir el campo "puesto"

  Escenario: Departamento fuera del catálogo es rechazado
    Cuando edito al empleado 1 con puesto "Analista" y departamento "Marketing"
    Entonces la API responde 422
    Y la pantalla indica que se debe corregir el campo "departamento"
    Y el empleado 1 conserva el departamento "Ventas"

  Escenario: Un empleado dado de baja no se puede editar
    Dado que el empleado 1 está dado de baja con fecha de baja "2026-10-01"
    Cuando edito al empleado 1 con puesto "Gerente" y departamento "Finanzas"
    Entonces la API responde 409
    Y el detail es "No se puede editar a un empleado dado de baja"
    Y el empleado 1 conserva el puesto "Analista" y el departamento "Ventas"

  # ---------- Baja ----------

  Escenario: Dar de baja a un empleado activo
    Cuando doy de baja al empleado 1 con fecha de baja "2026-11-06"
    Entonces la API responde 200
    Y el empleado 1 tiene estado "baja" y fecha_baja "2026-11-06"
    Y la pantalla muestra en "mensaje-exito" que la baja se registró

  Escenario: El empleado dado de baja sigue en el directorio marcado como Baja
    Cuando doy de baja al empleado 1 con fecha de baja "2026-11-06"
    Entonces "GET /api/empleados" sigue incluyendo al empleado 1
    Y "fila-empleado-1" aparece en "tabla-empleados"
    Y "estado-empleado-1" muestra el texto "Baja"
    Y "numero-empleado-1" muestra "EMP-0001"

  Escenario: Fecha de baja igual a la fecha de ingreso (límite permitido)
    Cuando doy de baja al empleado 1 con fecha de baja "2024-03-10"
    Entonces la API responde 200
    Y el empleado 1 tiene estado "baja" y fecha_baja "2024-03-10"

  Escenario: Fecha de baja un día anterior a la fecha de ingreso (primer valor inválido)
    Cuando doy de baja al empleado 1 con fecha de baja "2024-03-09"
    Entonces la API responde 422
    Y la pantalla indica que se debe corregir el campo "fecha_baja"
    Y el empleado 1 conserva el estado "activo" y fecha_baja vacía

  Escenario: Un empleado activo no tiene fecha de baja
    Cuando consulto al empleado 1 con "GET /api/empleados/1"
    Entonces el empleado 1 tiene estado "activo" y fecha_baja vacía

# Preguntas abiertas
# - Los endpoints exactos de edición y baja (método y ruta) no están en convenciones_app.md; los escenarios los describen sin fijarlos.
# - ¿Qué responde la API si se envía numero_empleado o correo al editar: se ignoran o dan 422? No hay regla ni mensaje.
# - ¿Cuál es el detail exacto para fecha de baja anterior al ingreso, puesto o departamento inválidos? Solo se sabe 422 y que la pantalla muestra el campo.
# - ¿Qué pasa si se da de baja a un empleado que ya está de baja (¿409 o se ignora?)?
# - ¿Se permite una fecha de baja futura?
# - ¿Qué responde editar o dar de baja a un id inexistente? (404 con qué mensaje; «Empleado no encontrado» solo aparece en vacaciones.)
# - ¿Se pueden editar nombre y fecha de ingreso? La historia solo menciona puesto y departamento.
# - Texto exacto de los mensajes de éxito de edición y baja.
