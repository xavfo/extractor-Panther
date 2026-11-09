"""Acceso a MySQL.

Se usa SQLAlchemy 2 con PyMySQL. La aplicación nunca arma SQL con datos del
usuario: todos los valores viajan como parámetros (`:nombre`), y los nombres de
tabla/columna salen de `app.esquema`, no de la URL.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterable, Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from .config import AJUSTES

_motor: Engine | None = None


def motor() -> Engine:
    """Motor compartido (pool con verificación previa)."""
    global _motor
    if _motor is None:
        _motor = create_engine(
            AJUSTES.base_datos_url,
            pool_pre_ping=True,
            pool_recycle=1800,
            future=True,
        )
    return _motor


def motor_servidor() -> Engine:
    """Motor sin base seleccionada, para crear la base si no existe."""
    return create_engine(AJUSTES.base_datos_sin_nombre, pool_pre_ping=True, future=True)


@contextmanager
def conexion() -> Iterator[Any]:
    with motor().begin() as con:
        yield con


def filas(sql: str, parametros: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    with conexion() as con:
        resultado = con.execute(text(sql), parametros or {})
        return [dict(fila) for fila in resultado.mappings().all()]


def fila(sql: str, parametros: dict[str, Any] | None = None) -> dict[str, Any] | None:
    resultado = filas(sql, parametros)
    return resultado[0] if resultado else None


def escalar(sql: str, parametros: dict[str, Any] | None = None) -> Any:
    with conexion() as con:
        return con.execute(text(sql), parametros or {}).scalar()


def ejecutar(sql: str, parametros: dict[str, Any] | None = None) -> None:
    with conexion() as con:
        con.execute(text(sql), parametros or {})


def ejecutar_muchos(sql: str, lote: Iterable[dict[str, Any]]) -> int:
    with conexion() as con:
        resultado = con.execute(text(sql), list(lote))
        return resultado.rowcount or 0


def disponible() -> bool:
    try:
        escalar("SELECT 1")
        return True
    except Exception:  # noqa: BLE001 - solo se usa para mostrar estado
        return False
