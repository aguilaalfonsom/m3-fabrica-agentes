export default function TablaEmpleados({ empleados, alEditar = () => {}, alBaja = () => {}, alVacaciones = () => {} }) {
  return (
    <>
    <table data-testid="tabla-empleados" style={{ width: "100%", borderCollapse: "collapse" }}>
      <thead>
        <tr>
          <th>Número</th>
          <th>Nombre</th>
          <th>Correo</th>
          <th>Puesto</th>
          <th>Departamento</th>
          <th>Ingreso</th>
          <th>Estado</th>
          <th>Acciones</th>
        </tr>
      </thead>
      <tbody>
        {empleados.map((e) => (
          <tr key={e.id} data-testid={`fila-empleado-${e.id}`}>
            <td data-testid={`numero-empleado-${e.id}`}>{e.numero_empleado}</td>
            <td>{e.nombre}</td>
            <td>{e.correo}</td>
            <td>{e.puesto}</td>
            <td>{e.departamento}</td>
            <td>{e.fecha_ingreso}</td>
            <td data-testid={`estado-empleado-${e.id}`}>{e.estado === "baja" ? "Baja" : "Activo"}</td>
            <td>
              {e.estado !== "baja" && (
                <>
                  <button data-testid={`editar-empleado-${e.id}`} onClick={() => alEditar(e)}>Editar</button>
                  <button data-testid={`baja-empleado-${e.id}`} onClick={() => alBaja(e)}>Dar de baja</button>
                  <button data-testid={`vacaciones-abrir-${e.id}`} onClick={() => alVacaciones(e)}>Solicitar vacaciones</button>
                </>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
    {empleados.length === 0 && <p data-testid="sin-resultados">No se encontraron empleados</p>}
    </>
  );
}
