import { useState } from "react";
import { darDeBajaEmpleado } from "./api.js";

// Formulario para dar de baja a un empleado; la validación de la fecha vive en el backend.
export default function FormularioBaja({ empleado, alTerminar, alCancelar }) {
  const [fecha, setFecha] = useState("");
  const [exito, setExito] = useState("");
  const [error, setError] = useState("");

  const confirmar = async (e) => {
    e.preventDefault();
    setExito("");
    setError("");
    try {
      await darDeBajaEmpleado(empleado.id, fecha);
      setExito("Baja registrada");
      alTerminar();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <form onSubmit={confirmar} noValidate style={{ display: "grid", gap: 8, marginBottom: 24 }}>
      <strong>Dar de baja a {empleado.nombre}</strong>
      <input
        data-testid="empleado-fecha-baja"
        type="date"
        value={fecha}
        onChange={(e) => setFecha(e.target.value)}
      />
      <button type="submit" data-testid="confirmar-baja">Confirmar baja</button>
      <button type="button" onClick={alCancelar}>Cancelar</button>
      {exito && <p data-testid="mensaje-exito" style={{ color: "green" }}>{exito}</p>}
      {error && <p data-testid="mensaje-error" style={{ color: "crimson" }}>{error}</p>}
    </form>
  );
}
