# language: es
Característica: Consultar el directorio de empleados
  Como persona del área de Recursos Humanos
  quiero ver el directorio, buscar por nombre o correo y filtrar por departamento
  para encontrar rápido a una persona

  Antecedentes:
    Dado que existen los siguientes empleados:
      | id | numero_empleado | nombre     | correo                 | puesto         | departamento     | estado |
      | 1  | EMP-0001        | Ana Pérez  | ana.perez@empresa.com  | Desarrolladora | Tecnología       | activo |
      | 2  | EMP-0002        | Luis Gómez | luis.gomez@empresa.com | Vendedor       | Ventas           | activo |
      | 3  | EMP-0003        | Marta Ruiz | marta.ruiz@empresa.com | Analista       | Finanzas         | baja   |
      | 4  | EMP-0004        | Ana Torres | atorres@empresa.com    | Reclutadora    | Recursos Humanos | activo |

  Escenario: Ver el directorio completo
    Dado que estoy en la aplicación sin texto de búsqueda ni filtro de departamento
    Cuando abro el directorio de empleados
    Entonces veo la tabla "tabla-empleados" con 4 filas
    Y la fila "fila-empleado-1" muestra "EMP-0001", "Ana Pérez", "Desarrolladora", "Tecnología" y "Activo"
    Y "numero-empleado-2" muestra "EMP-0002"

  Escenario: Un empleado dado de baja sigue apareciendo en el directorio
    Dado que el empleado "EMP-0003" tiene estado "baja"
    Cuando abro el directorio de empleados
    Entonces la fila "fila-empleado-3" está visible
    Y "estado-empleado-3" muestra "Baja"

  Escenario: Consultar el directorio por API
    Dado que hay 4 empleados registrados
    Cuando hago GET /api/empleados
    Entonces recibo 200 con una lista de 4 empleados
    Y cada empleado incluye los campos "id", "numero_empleado", "nombre", "correo", "puesto", "departamento", "fecha_ingreso", "estado", "fecha_baja" y "creado_en"

  Escenario: Buscar por nombre
    Dado que estoy en el directorio con las 4 filas visibles
    Cuando escribo "Luis" en "buscar-empleados"
    Entonces solo veo la fila "fila-empleado-2"

  Escenario: Buscar por correo
    Dado que estoy en el directorio con las 4 filas visibles
    Cuando escribo "marta.ruiz@empresa.com" en "buscar-empleados"
    Entonces solo veo la fila "fila-empleado-3"

  Escenario: La búsqueda por nombre no distingue mayúsculas en mayúsculas
    Dado que estoy en el directorio con las 4 filas visibles
    Cuando escribo "LUIS GÓMEZ" en "buscar-empleados"
    Entonces solo veo la fila "fila-empleado-2"

  Escenario: La búsqueda por nombre no distingue mayúsculas en minúsculas
    Dado que estoy en el directorio con las 4 filas visibles
    Cuando escribo "luis gómez" en "buscar-empleados"
    Entonces solo veo la fila "fila-empleado-2"

  Escenario: La búsqueda por correo no distingue mayúsculas de minúsculas
    Dado que estoy en el directorio con las 4 filas visibles
    Cuando escribo "ATORRES@EMPRESA.COM" en "buscar-empleados"
    Entonces solo veo la fila "fila-empleado-4"

  Escenario: La búsqueda por texto parcial devuelve varias coincidencias
    Dado que estoy en el directorio con las 4 filas visibles
    Cuando escribo "ana" en "buscar-empleados"
    Entonces veo las filas "fila-empleado-1" y "fila-empleado-4"
    Y no veo las demás filas

  Escenario: Filtrar por departamento
    Dado que estoy en el directorio con las 4 filas visibles
    Cuando elijo "Ventas" en "filtro-departamento"
    Entonces solo veo la fila "fila-empleado-2"

  Escenario: Filtrar por un departamento válido sin empleados
    Dado que ningún empleado pertenece al departamento "Operaciones"
    Cuando elijo "Operaciones" en "filtro-departamento"
    Entonces no veo ninguna fila
    Y veo el elemento "sin-resultados"

  Escenario: Combinar búsqueda y filtro de departamento
    Dado que estoy en el directorio con las 4 filas visibles
    Cuando escribo "ana" en "buscar-empleados"
    Y elijo "Tecnología" en "filtro-departamento"
    Entonces solo veo la fila "fila-empleado-1"

  Escenario: Búsqueda y filtro sin coincidencia conjunta
    Dado que estoy en el directorio con las 4 filas visibles
    Cuando escribo "Luis" en "buscar-empleados"
    Y elijo "Finanzas" en "filtro-departamento"
    Entonces no veo ninguna fila
    Y veo el elemento "sin-resultados"

  Escenario: Búsqueda sin resultados muestra un mensaje
    Dado que estoy en el directorio con las 4 filas visibles
    Cuando escribo "Zacarías" en "buscar-empleados"
    Entonces no veo ninguna fila en "tabla-empleados"
    Y veo el elemento "sin-resultados" con un mensaje que indica que no hay resultados

  Escenario: Limpiar la búsqueda restaura el directorio
    Dado que escribí "Zacarías" en "buscar-empleados" y veo "sin-resultados"
    Cuando borro el texto de "buscar-empleados"
    Entonces veo las 4 filas
    Y no veo el elemento "sin-resultados"

  Escenario: El mensaje de sin resultados no aparece cuando hay coincidencias
    Dado que estoy en el directorio con las 4 filas visibles
    Cuando escribo "Ana" en "buscar-empleados"
    Entonces no veo el elemento "sin-resultados"

  Escenario: Directorio vacío
    Dado que no hay empleados registrados
    Cuando abro el directorio de empleados
    Entonces veo el elemento "sin-resultados"

# Preguntas abiertas
# - ¿Cuál es el texto exacto del mensaje de "sin resultados"? El contexto no lo define; los escenarios solo verifican que "sin-resultados" sea visible.
# - ¿La búsqueda y el filtro se hacen en el servidor (parámetros de GET /api/empleados, ¿con qué nombres?) o en el cliente? El contexto no define los parámetros de consulta.
# - ¿La búsqueda es por coincidencia parcial (contiene) o por prefijo? Se asumió "contiene" en el escenario de "ana"; confirmar.
# - ¿Se ignoran espacios al inicio/fin del texto buscado? ¿Y los acentos ("Gomez" vs "Gómez")?
# - ¿Orden del directorio? No está definido (se asume por número de empleado).
# - ¿Se pagina el directorio si hay muchos empleados?
# - ¿El filtro de departamento tiene una opción "Todos" y con qué texto?
