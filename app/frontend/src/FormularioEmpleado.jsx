import { useEffect, useState } from "react";
import { crearEmpleado, editarEmpleado, listarDepartamentos } from "./api.js";

const VACIO = { nombre: "", correo: "", puesto: "", departamento: "", fecha_ingreso: "" };

export default function FormularioEmpleado({ alGuardar, empleadoEditando = null, alCancelar = () => {} }) {
  const editando = Boolean(empleadoEditando);
  const [datos, setDatos] = useState(
    editando
      ? { ...VACIO, puesto: empleadoEditando.puesto, departamento: empleadoEditando.departamento }
      : VACIO
  );
  const [departamentos, setDepartamentos] = useState([]);
  const [exito, setExito] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    listarDepartamentos().then(setDepartamentos).catch(() => setDepartamentos([]));
  }, []);

  const cambiar = (campo) => (e) => setDatos({ ...datos, [campo]: e.target.value });

  // noValidate: las reglas viven en el backend y sus mensajes deben llegar a la pantalla.
  const enviar = async (e) => {
    e.preventDefault();
    setExito("");
    setError("");
    try {
      if (editando) {
        await editarEmpleado(empleadoEditando.id, datos);
        setExito("Cambio guardado");
        alGuardar();
        return;
      }
      const nuevo = await crearEmpleado(datos);
      setExito(`Empleado registrado con número ${nuevo.numero_empleado}`);
      setDatos(VACIO);
      alGuardar();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <form onSubmit={enviar} noValidate style={{ display: "grid", gap: 8, marginBottom: 24 }}>
      {editando && <strong>Editando a {empleadoEditando.nombre} ({empleadoEditando.numero_empleado})</strong>}
      {!editando && (
        <>
          <input data-testid="empleado-nombre" placeholder="Nombre" value={datos.nombre} onChange={cambiar("nombre")} />
          <input data-testid="empleado-correo" placeholder="Correo" value={datos.correo} onChange={cambiar("correo")} />
        </>
      )}
      <input data-testid="empleado-puesto" placeholder="Puesto" value={datos.puesto} onChange={cambiar("puesto")} />
      <select data-testid="empleado-departamento" value={datos.departamento} onChange={cambiar("departamento")}>
        <option value="">Selecciona un departamento</option>
        {departamentos.map((d) => (
          <option key={d} value={d}>{d}</option>
        ))}
      </select>
      {!editando && (
        <input
          data-testid="empleado-fecha-ingreso"
          type="date"
          value={datos.fecha_ingreso}
          onChange={cambiar("fecha_ingreso")}
        />
      )}
      <button type="submit" data-testid="empleado-guardar">Guardar</button>
      {editando && <button type="button" onClick={alCancelar}>Cancelar</button>}
      {exito && <p data-testid="mensaje-exito" style={{ color: "green" }}>{exito}</p>}
      {error && <p data-testid="mensaje-error" style={{ color: "crimson" }}>{error}</p>}
    </form>
  );
}
