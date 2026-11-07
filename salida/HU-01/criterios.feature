# language: es
Característica: Registrar empleado
  Como persona del área de Recursos Humanos
  quiero registrar a un empleado con nombre, correo corporativo, puesto, departamento y fecha de ingreso
  para darlo de alta en la empresa

  Escenario: Registro exitoso del primer empleado
    Dado que no hay empleados registrados y hoy es 2026-11-06
    Cuando envío POST /api/empleados con nombre "Ana Pérez", correo "ana.perez@empresa.com", puesto "Analista", departamento "Tecnología" y fecha_ingreso "2026-01-15"
    Entonces la API responde 201
    Y el empleado guardado tiene numero_empleado "EMP-0001"
    Y el estado es "activo"
    Y fecha_baja es nula
    Y creado_en contiene la fecha y hora del registro

  Escenario: La pantalla muestra confirmación con el número asignado
    Dado que no hay empleados registrados y estoy en el formulario de registro
    Cuando escribo "Ana Pérez" en empleado-nombre, "ana.perez@empresa.com" en empleado-correo, "Analista" en empleado-puesto, elijo "Tecnología" en empleado-departamento, escribo "2026-01-15" en empleado-fecha-ingreso y pulso empleado-guardar
    Entonces mensaje-exito es visible y contiene "EMP-0001"
    Y la fila del nuevo empleado en tabla-empleados muestra "EMP-0001" en numero-empleado-{id}
    Y estado-empleado-{id} muestra "Activo"

  Escenario: El número de empleado es consecutivo
    Dado que existe un empleado registrado con numero_empleado "EMP-0001"
    Cuando registro a "Luis Gómez" con correo "luis.gomez@empresa.com", puesto "Vendedor", departamento "Ventas" y fecha_ingreso "2026-02-02"
    Entonces la API responde 201
    Y el nuevo empleado tiene numero_empleado "EMP-0002"

  Escenario: El número de empleado lo asigna el sistema aunque se envíe uno
    Dado que no hay empleados registrados
    Cuando envío POST /api/empleados con numero_empleado "EMP-0999" además de los datos válidos de "Ana Pérez"
    Entonces la API responde 201
    Y el empleado guardado tiene numero_empleado "EMP-0001"

  Escenario: El correo se guarda en minúsculas
    Dado que no existe ningún empleado con el correo "marta.ruiz@empresa.com"
    Cuando registro a "Marta Ruiz" con correo "Marta.Ruiz@empresa.com" y datos válidos
    Entonces la API responde 201
    Y el correo guardado es "marta.ruiz@empresa.com"

  Escenario: Departamento "Recursos Humanos" del catálogo es aceptado
    Dado que GET /api/departamentos devuelve Tecnología, Ventas, Finanzas, Recursos Humanos y Operaciones
    Cuando registro a "Eva Soto" con correo "eva.soto@empresa.com" y departamento "Recursos Humanos"
    Entonces la API responde 201
    Y el departamento guardado es "Recursos Humanos"

  Escenario: Correo duplicado con el mismo texto
    Dado que existe un empleado con correo "ana.perez@empresa.com"
    Cuando registro a otra persona con correo "ana.perez@empresa.com"
    Entonces la API responde 409
    Y el detail es "El correo ya está registrado"
    Y no se crea ningún empleado nuevo

  Escenario: Correo duplicado sin importar mayúsculas
    Dado que existe un empleado con correo "ana.perez@empresa.com"
    Cuando registro a otra persona con correo "ANA.PEREZ@empresa.com"
    Entonces la API responde 409
    Y el detail es "El correo ya está registrado"

  Escenario: La pantalla muestra el error de correo duplicado
    Dado que existe un empleado con correo "ana.perez@empresa.com" y estoy en el formulario de registro
    Cuando completo el formulario con el correo "ana.perez@empresa.com" y pulso empleado-guardar
    Entonces mensaje-error es visible y contiene "El correo ya está registrado"

  Escenario: Correo con dominio distinto al corporativo
    Dado que estoy registrando a un empleado con datos válidos
    Cuando envío el correo "ana.perez@gmail.com"
    Entonces la API responde 422
    Y el detail es "Usa el correo corporativo @empresa.com"

  Escenario: Correo sin arroba ni dominio
    Dado que estoy registrando a un empleado con datos válidos
    Cuando envío el correo "ana.perez"
    Entonces la API responde 422
    Y el detail es "Usa el correo corporativo @empresa.com"

  Escenario: La pantalla muestra el error de dominio de correo
    Dado que estoy en el formulario de registro con datos válidos
    Cuando escribo "ana.perez@otraempresa.com" en empleado-correo y pulso empleado-guardar
    Entonces mensaje-error es visible y contiene "Usa el correo corporativo @empresa.com"

  Escenario: Fecha de ingreso de hoy es válida (límite)
    Dado que hoy es 2026-11-06
    Cuando registro a un empleado con datos válidos y fecha_ingreso "2026-11-06"
    Entonces la API responde 201

  Escenario: Fecha de ingreso de mañana ya no es válida (límite)
    Dado que hoy es 2026-11-06
    Cuando registro a un empleado con datos válidos y fecha_ingreso "2026-11-07"
    Entonces la API responde 422
    Y el detail es "La fecha de ingreso no puede ser futura"
    Y no se crea ningún empleado

  Escenario: Fecha de ingreso en el pasado es válida
    Dado que hoy es 2026-11-06
    Cuando registro a un empleado con datos válidos y fecha_ingreso "2025-12-21"
    Entonces la API responde 201

  Escenario: La pantalla muestra el error de fecha futura
    Dado que hoy es 2026-11-06 y estoy en el formulario de registro con datos válidos
    Cuando escribo "2026-12-01" en empleado-fecha-ingreso y pulso empleado-guardar
    Entonces mensaje-error es visible y contiene "La fecha de ingreso no puede ser futura"

  Escenario: Nombre de 2 caracteres es válido (límite)
    Dado que estoy registrando a un empleado con datos válidos
    Cuando envío el nombre "Li"
    Entonces la API responde 201

  Escenario: Nombre de 1 carácter no es válido (límite)
    Dado que estoy registrando a un empleado con datos válidos
    Cuando envío el nombre "L"
    Entonces la API responde 422
    Y la pantalla indica que se debe corregir el campo nombre

  Escenario: Nombre de 80 caracteres es válido (límite)
    Dado que estoy registrando a un empleado con datos válidos
    Cuando envío un nombre de 80 caracteres "A"
    Entonces la API responde 201

  Escenario: Nombre de 81 caracteres no es válido (límite)
    Dado que estoy registrando a un empleado con datos válidos
    Cuando envío un nombre de 81 caracteres "A"
    Entonces la API responde 422
    Y la pantalla indica que se debe corregir el campo nombre

  Escenario: Nombre vacío
    Dado que estoy registrando a un empleado con datos válidos
    Cuando dejo el nombre vacío
    Entonces la API responde 422
    Y la pantalla indica que se debe corregir el campo nombre

  Escenario: Puesto de 2 caracteres es válido (límite)
    Dado que estoy registrando a un empleado con datos válidos
    Cuando envío el puesto "TI"
    Entonces la API responde 201

  Escenario: Puesto de 1 carácter no es válido (límite)
    Dado que estoy registrando a un empleado con datos válidos
    Cuando envío el puesto "T"
    Entonces la API responde 422
    Y la pantalla indica que se debe corregir el campo puesto

  Escenario: Puesto de 60 caracteres es válido (límite)
    Dado que estoy registrando a un empleado con datos válidos
    Cuando envío un puesto de 60 caracteres "B"
    Entonces la API responde 201

  Escenario: Puesto de 61 caracteres no es válido (límite)
    Dado que estoy registrando a un empleado con datos válidos
    Cuando envío un puesto de 61 caracteres "B"
    Entonces la API responde 422
    Y la pantalla indica que se debe corregir el campo puesto

  Escenario: Puesto vacío
    Dado que estoy registrando a un empleado con datos válidos
    Cuando dejo el puesto vacío
    Entonces la API responde 422
    Y la pantalla indica que se debe corregir el campo puesto

  Escenario: Departamento fuera del catálogo
    Dado que estoy registrando a un empleado con datos válidos
    Cuando envío el departamento "Marketing"
    Entonces la API responde 422
    Y la pantalla indica que se debe corregir el campo departamento

  Escenario: Correo vacío
    Dado que estoy registrando a un empleado con datos válidos
    Cuando dejo el correo vacío
    Entonces la API responde 422
    Y la pantalla indica que se debe corregir el campo correo

  Escenario: Fecha de ingreso vacía
    Dado que estoy registrando a un empleado con datos válidos
    Cuando dejo la fecha de ingreso vacía
    Entonces la API responde 422
    Y la pantalla indica que se debe corregir el campo fecha de ingreso

# Preguntas abiertas
# - El detail exacto de los 422 por datos inválidos distintos de correo y fecha futura no está definido en el contexto; solo se sabe que la pantalla muestra qué campo corregir.
# - Un correo con el dominio en mayúsculas (por ejemplo "ana@EMPRESA.COM") ¿es válido? El contexto solo dice que se guarda en minúsculas.
# - Un nombre o puesto formado solo por espacios, ¿cuenta como vacío?
