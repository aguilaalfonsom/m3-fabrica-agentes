import { useEffect, useRef, useState } from "react";
import { listarDepartamentos, listarEmpleados } from "./api.js";
import BarraFiltros from "./BarraFiltros.jsx";
import FormularioBaja from "./FormularioBaja.jsx";
import FormularioEmpleado from "./FormularioEmpleado.jsx";
import FormularioVacaciones from "./FormularioVacaciones.jsx";
import TablaEmpleados from "./TablaEmpleados.jsx";

export default function App() {
  const [empleados, setEmpleados] = useState([]);
  const [departamentos, setDepartamentos] = useState([]);
  const [buscar, setBuscar] = useState("");
  const [departamento, setDepartamento] = useState("");
  const [editando, setEditando] = useState(null);
  const [dandoDeBaja, setDandoDeBaja] = useState(null);
  const [conVacaciones, setConVacaciones] = useState(null);
  const ultimaPeticion = useRef(0);
  const filtros = useRef({ buscar, departamento });
  filtros.current = { buscar, departamento };

  const refrescar = async () => {
    const numero = ++ultimaPeticion.current;
    try {
      const lista = await listarEmpleados(filtros.current);
      // Se descarta una respuesta vieja si ya hay una petición más reciente.
      if (numero === ultimaPeticion.current) setEmpleados(lista);
    } catch {
      if (numero === ultimaPeticion.current) setEmpleados([]);
    }
  };

  useEffect(() => {
    listarDepartamentos().then(setDepartamentos).catch(() => setDepartamentos([]));
  }, []);

  // Debounce corto para no consultar en cada tecla.
  useEffect(() => {
    const temporizador = setTimeout(refrescar, 250);
    return () => clearTimeout(temporizador);
  }, [buscar, departamento]);

  return (
    <main style={{ fontFamily: "sans-serif", maxWidth: 900, margin: "0 auto", padding: 16 }}>
      <h1>Gestión de empleados</h1>
      {conVacaciones ? (
        <FormularioVacaciones
          key={`vacaciones-${conVacaciones.id}`}
          empleado={conVacaciones}
          alCancelar={() => setConVacaciones(null)}
        />
      ) : dandoDeBaja ? (
        <FormularioBaja
          key={`baja-${dandoDeBaja.id}`}
          empleado={dandoDeBaja}
          alTerminar={refrescar}
          alCancelar={() => setDandoDeBaja(null)}
        />
      ) : (
        <FormularioEmpleado
          key={editando ? `editar-${editando.id}` : "nuevo"}
          empleadoEditando={editando}
          alGuardar={refrescar}
          alCancelar={() => setEditando(null)}
        />
      )}
      <BarraFiltros
        buscar={buscar}
        departamento={departamento}
        departamentos={departamentos}
        alCambiarBuscar={setBuscar}
        alCambiarDepartamento={setDepartamento}
      />
      <TablaEmpleados
        empleados={empleados}
        alEditar={(e) => {
          setConVacaciones(null);
          setDandoDeBaja(null);
          setEditando(e);
        }}
        alVacaciones={(e) => {
          setEditando(null);
          setDandoDeBaja(null);
          setConVacaciones(e);
        }}
        alBaja={(e) => {
          setConVacaciones(null);
          setEditando(null);
          setDandoDeBaja(e);
        }}
      />
    </main>
  );
}
