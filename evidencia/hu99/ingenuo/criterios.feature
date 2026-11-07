# language: es
Característica: Exportar la plantilla de empleados
  Como persona del área de Recursos Humanos
  quiero descargar el directorio de empleados en CSV
  para compartirlo con el área de nómina

  Antecedentes:
    Dado que existen empleados registrados en el directorio

  Escenario: Descargar el directorio en CSV
    Cuando solicito exportar la plantilla de empleados
    Entonces se descarga un archivo en formato CSV
    Y el archivo tiene las columnas "numero_empleado", "nombre", "puesto", "departamento" y "estado"
    Y hay una fila por cada empleado del directorio

  Escenario: El archivo no incluye datos fuera de los acordados
    Cuando solicito exportar la plantilla de empleados
    Entonces el archivo no contiene la columna "correo"
    Y el archivo no contiene las columnas "fecha_ingreso", "fecha_baja" ni "creado_en"

  Escenario: Los empleados dados de baja siguen apareciendo en la exportación
    Dado que el empleado "EMP-0002" fue dado de baja
    Cuando solicito exportar la plantilla de empleados
    Entonces el archivo incluye una fila para "EMP-0002"
    Y el estado de esa fila es "baja"

  Escenario: Los empleados activos se exportan con estado activo
    Dado que el empleado "EMP-0001" está activo
    Cuando solicito exportar la plantilla de empleados
    Entonces el estado de la fila de "EMP-0001" es "activo"

  Escenario: Exportar un directorio sin empleados
    Dado que no hay empleados registrados
    Cuando solicito exportar la plantilla de empleados
    Entonces se descarga un archivo CSV que solo contiene la fila de encabezados
