"""Checkpointer en disco: guarda el estado del grafo en cada paso para poder pausar y reanudar.

Es un InMemorySaver que, además, vuelca su contenido a `checkpoints.pkl` después de cada escritura
y lo recupera al arrancar. Con el mismo thread_id (uno por historia) una ejecución que quedó en
pausa —por ejemplo, esperando la aprobación del plan— se retoma donde se quedó, aunque se haya
cerrado la terminal. (SqliteSaver no tiene versión compatible con langgraph 1.2 en Windows ARM.)
"""
import pickle
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver


class CheckpointerDisco(InMemorySaver):
    def __init__(self, archivo: Path):
        super().__init__()
        self.archivo = archivo
        if archivo.exists():
            datos = pickle.loads(archivo.read_bytes())
            for hilo, espacios in datos.get("storage", {}).items():
                for ns, pasos in espacios.items():
                    self.storage[hilo][ns].update(pasos)      # conserva los defaultdict internos
            self.writes.update(datos.get("writes", {}))
            self.blobs.update(datos.get("blobs", {}))

    def _volcar(self) -> None:
        datos = {nombre: dict(getattr(self, nombre)) for nombre in ("storage", "writes", "blobs")}
        datos["storage"] = {k: {ns: dict(v) for ns, v in d.items()} for k, d in datos["storage"].items()}
        self.archivo.write_bytes(pickle.dumps(datos))

    def put(self, *args, **kwargs):
        resultado = super().put(*args, **kwargs)
        self._volcar()
        return resultado

    def put_writes(self, *args, **kwargs):
        resultado = super().put_writes(*args, **kwargs)
        self._volcar()
        return resultado

    def delete_thread(self, thread_id: str) -> None:
        super().delete_thread(thread_id)
        self._volcar()
