export default function BarraFiltros({ buscar, departamento, departamentos, alCambiarBuscar, alCambiarDepartamento }) {
  return (
    <div style={{ display: "flex", gap: 8, margin: "16px 0" }}>
      <input
        type="text"
        data-testid="buscar-empleados"
        placeholder="Buscar por nombre o correo"
        value={buscar}
        onChange={(e) => alCambiarBuscar(e.target.value)}
        style={{ flex: 1 }}
      />
      <select
        data-testid="filtro-departamento"
        value={departamento}
        onChange={(e) => alCambiarDepartamento(e.target.value)}
      >
        <option value="">Todos los departamentos</option>
        {departamentos.map((d) => (
          <option key={d} value={d}>
            {d}
          </option>
        ))}
      </select>
    </div>
  );
}
