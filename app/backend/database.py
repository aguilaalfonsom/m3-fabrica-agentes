"""Conexión a SQLite y sesión de SQLAlchemy."""
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

CARPETA_DATOS = Path(__file__).parent / "datos"
CARPETA_DATOS.mkdir(exist_ok=True)

motor = create_engine(
    f"sqlite:///{CARPETA_DATOS / 'empleados.db'}",
    connect_args={"check_same_thread": False},
)
Sesion = sessionmaker(bind=motor, autoflush=False)


class Base(DeclarativeBase):
    pass


def obtener_db():
    db = Sesion()
    try:
        yield db
    finally:
        db.close()
