// Cliente de la API: rutas relativas; ante un error lanza el `detail` tal cual.
async function pedir(ruta, opciones) {
  const resp = await fetch(ruta, opciones);
  let cuerpo = null;
  try {
    cuerpo = await resp.json();
  } catch {
    cuerpo = null;
  }
  if (!resp.ok) {
    const detail = cuerpo && typeof cuerpo.detail === "string" ? cuerpo.detail : "Error inesperado";
    throw new Error(detail);
  }
  return cuerpo;
}

export const listarEmpleados = ({ buscar = "", departamento = "" } = {}) => {
  const params = new URLSearchParams();
  if (buscar) params.set("buscar", buscar);
  if (departamento) params.set("departamento", departamento);
  const consulta = params.toString();
  return pedir(consulta ? `/api/empleados?${consulta}` : "/api/empleados");
};
export const listarDepartamentos = () => pedir("/api/departamentos");
export const editarEmpleado = (id, { puesto, departamento }) =>
  pedir(`/api/empleados/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ puesto, departamento }),
  });
export const darDeBajaEmpleado = (id, fecha_baja) =>
  pedir(`/api/empleados/${id}/baja`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fecha_baja }),
  });
export const solicitarVacaciones = (id, fecha_inicio, fecha_fin) =>
  pedir(`/api/empleados/${id}/vacaciones`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fecha_inicio, fecha_fin }),
  });
export const consultarSaldo = (id, anio) =>
  pedir(`/api/empleados/${id}/vacaciones${anio ? `?anio=${anio}` : ""}`);
export const crearEmpleado = (datos) =>
  pedir("/api/empleados", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(datos),
  });
