import { useEffect, useState } from "react";
import { consultarSaldo, solicitarVacaciones } from "./api.js";

// Formulario de vacaciones: el cálculo y las reglas viven en el backend.
export default function FormularioVacaciones({ empleado, alCancelar }) {
  const [inicio, setInicio] = useState("");
  const [fin, setFin] = useState("");
  const [disponibles, setDisponibles] = useState("");
  const [mensaje, setMensaje] = useState("");
  const [esError, setEsError] = useState(false);

  const cargarSaldo = async (anio) => {
    try {
      const saldo = await consultarSaldo(empleado.id, anio);
      setDisponibles(saldo.dias_disponibles);
    } catch {
      setDisponibles("");
    }
  };

  useEffect(() => {
    cargarSaldo();
  }, [empleado.id]);

  const enviar = async (e) => {
    e.preventDefault();
    setMensaje("");
    // El saldo se vuelve a pedir para el año de la solicitud (lo calcula la API).
    const anio = /^\d{4}-/.test(inicio) ? inicio.slice(0, 4) : undefined;
    try {
      const r = await solicitarVacaciones(empleado.id, inicio, fin);
      setEsError(false);
      setMensaje(
        `Solicitud registrada: ${r.dias_habiles} días hábiles. Te quedan ${r.dias_restantes} días hábiles en ${r.fecha_inicio.slice(0, 4)}.`
      );
    } catch (err) {
      setEsError(true);
      setMensaje(err.message);
    }
    await cargarSaldo(anio);
  };

  return (
    <form onSubmit={enviar} noValidate style={{ display: "grid", gap: 8, marginBottom: 24 }}>
      <strong>Solicitar vacaciones de {empleado.nombre}</strong>
      <p>
        Días disponibles: <span data-testid="vacaciones-disponibles">{disponibles}</span>
      </p>
      <input
        data-testid="vacaciones-fecha-inicio"
        type="date"
        value={inicio}
        onChange={(e) => setInicio(e.target.value)}
      />
      <input
        data-testid="vacaciones-fecha-fin"
        type="date"
        value={fin}
        onChange={(e) => setFin(e.target.value)}
      />
      <button type="submit" data-testid="vacaciones-enviar">Enviar solicitud</button>
      <button type="button" onClick={alCancelar}>Cancelar</button>
      {mensaje && (
        <p data-testid="vacaciones-mensaje" style={{ color: esError ? "crimson" : "green" }}>
          {mensaje}
        </p>
      )}
    </form>
  );
}
