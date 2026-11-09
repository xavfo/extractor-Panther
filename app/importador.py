"""Importación de los XLSX de Panther a MySQL.

El importador es idempotente: se puede correr varias veces al día y cada corrida
actualiza las filas existentes (misma clave) e inserta las nuevas. Nunca borra:
si un paciente desaparece del export, se queda en la base y se ve en la fecha de
la última importación. Cada corrida queda registrada en `importaciones`.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import text

from . import db
from .config import AJUSTES
from .esquema import (
    COLUMNAS_OMITIDAS,
    TABLAS,
    Tabla,
    asegurar_tabla,
    asegurar_tablas_propias,
    tipo_columna,
)
from .limpieza import convertir, texto

_NOMBRE_VALIDO = re.compile(r"^[A-Za-z0-9_]+$")
_LOTE = 400


def crear_base_si_falta() -> None:
    if not _NOMBRE_VALIDO.match(AJUSTES.db_nombre):
        raise ValueError(f"Nombre de base inválido: {AJUSTES.db_nombre!r}")
    motor = db.motor_servidor()
    with motor.connect() as con:
        con.execute(text(
            f"CREATE DATABASE IF NOT EXISTS `{AJUSTES.db_nombre}` "
            "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        ))
        con.commit()


def _leer_archivo(ruta: Path) -> pd.DataFrame:
    marco = pd.read_excel(ruta, dtype=str, sheet_name=0)
    marco.columns = [str(columna).strip() for columna in marco.columns]
    return marco


def _huella_fila(fila: dict[str, Any]) -> str:
    """Identificador estable de una fila sin clave natural.

    Se calcula sobre todos los valores ya normalizados, así dos corridas del
    mismo export producen la misma huella y no se duplica nada.
    """
    partes = [
        "" if fila[columna] is None else str(fila[columna])
        for columna in sorted(fila)
        if columna != "_huella"
    ]
    return hashlib.sha1("\x1f".join(partes).encode("utf-8")).hexdigest()


def _preparar_filas(
    tabla: Tabla, marco: pd.DataFrame
) -> tuple[dict[tuple[Any, ...], dict[str, Any]], int, list[str]]:
    """Convierte el DataFrame a filas listas para MySQL.

    Devuelve (registros por clave, cantidad de duplicados descartados,
    advertencias). Si la clave viene vacía, la fila se descarta y se advierte.
    """
    columnas = [
        columna for columna in marco.columns if columna not in COLUMNAS_OMITIDAS
    ]
    tipos = {columna: tipo_columna(columna) for columna in columnas}
    registros: dict[tuple[Any, ...], dict[str, Any]] = {}
    duplicados = 0
    sin_clave = 0
    valores_invalidos = 0

    for _, fila in marco.iterrows():
        convertida: dict[str, Any] = {}
        for columna in columnas:
            valor_original = fila[columna]
            try:
                convertida[columna] = convertir(valor_original, tipos[columna])
            except Exception:  # noqa: BLE001 - un dato malo no debe tumbar la tabla
                convertida[columna] = None
                valores_invalidos += 1
        if "_huella" in tabla.clave:
            convertida["_huella"] = _huella_fila(convertida)
        clave = tuple(convertida.get(columna) for columna in tabla.clave)
        if any(parte is None or parte == "" for parte in clave):
            sin_clave += 1
            continue
        if clave in registros:
            duplicados += 1
        registros[clave] = convertida

    advertencias: list[str] = []
    if duplicados:
        advertencias.append(f"{duplicados} filas con clave repetida (se conservó la última)")
    if sin_clave:
        advertencias.append(f"{sin_clave} filas sin clave (descartadas)")
    if valores_invalidos:
        advertencias.append(f"{valores_invalidos} valores no convertibles (quedaron NULL)")
    return registros, duplicados, advertencias


def _promover_texto_largo(tabla: Tabla, registros: list[dict[str, Any]]) -> None:
    """Si un texto supera los 255 caracteres, la columna pasa a TEXT.

    Evita truncar datos clínicos (por ejemplo, una nota larga) sin obligar a
    mantener una lista manual de columnas.
    """
    from .db import conexion

    for columna in registros[0].keys():
        if tipo_columna(columna) != "VARCHAR(255)":
            continue
        largo = max((len(valor) for valor in (r[columna] for r in registros)
                     if isinstance(valor, str)), default=0)
        if largo <= 255:
            continue
        with conexion() as con:
            con.execute(text(
                f"ALTER TABLE `{tabla.nombre}` MODIFY `{columna}` LONGTEXT NULL"
            ))


def _purgar_sobrantes(tabla: Tabla, registros: list[dict[str, Any]]) -> int:
    """Retira filas que ya no vienen en el export (solo tablas reemplazables).

    Se usa en tablas sin clave natural, como la agenda, donde una cita
    modificada produce una huella nueva. Si el archivo llega vacío no se purga
    nada: se prefiere conservar lo anterior antes que vaciar por un export malo.
    """
    if not registros:
        return 0
    actuales = {registro["_huella"] for registro in registros}
    existentes = {
        fila["_huella"]
        for fila in db.filas(f"SELECT `_huella` FROM `{tabla.nombre}`")
    }
    sobrantes = list(existentes - actuales)
    borradas = 0
    for inicio in range(0, len(sobrantes), 300):
        lote = sobrantes[inicio:inicio + 300]
        parametros = {f"h{indice}": valor for indice, valor in enumerate(lote)}
        lista = ", ".join(f":h{indice}" for indice in range(len(lote)))
        db.ejecutar(
            f"DELETE FROM `{tabla.nombre}` WHERE `_huella` IN ({lista})",
            parametros,
        )
        borradas += len(lote)
    return borradas


def _sentencia_upsert(tabla: Tabla, columnas: list[str]) -> str:
    marcas = ", ".join(f":{columna}" for columna in columnas)
    lista = ", ".join(f"`{columna}`" for columna in columnas)
    actualizables = [columna for columna in columnas if columna not in tabla.clave]
    if not actualizables:
        return f"INSERT INTO `{tabla.nombre}` ({lista}) VALUES ({marcas})"
    cambios = ", ".join(f"`{columna}`=VALUES(`{columna}`)" for columna in actualizables)
    return (
        f"INSERT INTO `{tabla.nombre}` ({lista}) VALUES ({marcas}) "
        f"ON DUPLICATE KEY UPDATE {cambios}"
    )


def _importar_tabla(tabla: Tabla, carpeta: Path) -> dict[str, Any]:
    ruta = carpeta / tabla.archivo
    resultado: dict[str, Any] = {
        "tabla": tabla.nombre,
        "archivo": tabla.archivo,
        "filas": 0,
        "columnas": 0,
        "error": None,
        "advertencias": [],
    }
    if not ruta.exists():
        resultado["error"] = f"No se encontró {tabla.archivo}"
        return resultado

    marco = _leer_archivo(ruta)
    resultado["columnas"] = len(marco.columns)
    cambios = asegurar_tabla(tabla, list(marco.columns))
    if cambios.recreada:
        resultado["advertencias"].append("tabla reconstruida por cambio de clave")
    if cambios.agregadas:
        resultado["advertencias"].append(
            f"columnas nuevas: {', '.join(cambios.agregadas)}"
        )

    registros_por_clave, _, advertencias = _preparar_filas(tabla, marco)
    resultado["advertencias"].extend(advertencias)
    registros = list(registros_por_clave.values())
    if not registros:
        return resultado

    if tabla.reemplazar:
        retiradas = _purgar_sobrantes(tabla, registros)
        if retiradas:
            resultado["advertencias"].append(
                f"{retiradas} filas retiradas (ya no vienen en el export)"
            )

    _promover_texto_largo(tabla, registros)
    columnas = list(registros[0].keys())
    sentencia = _sentencia_upsert(tabla, columnas)
    for inicio in range(0, len(registros), _LOTE):
        db.ejecutar_muchos(sentencia, registros[inicio:inicio + _LOTE])

    resultado["filas"] = len(registros)
    return resultado


def importar(carpeta: Path | None = None) -> dict[str, Any]:
    """Importa todas las tablas y deja el registro de la corrida."""
    origen = Path(carpeta or AJUSTES.ruta_exportacion)
    if not origen.exists():
        raise FileNotFoundError(f"No existe la carpeta de exportación: {origen}")

    crear_base_si_falta()
    asegurar_tablas_propias()

    inicio = datetime.now()
    with db.conexion() as con:
        resultado = con.execute(
            text(
                "INSERT INTO importaciones (iniciada_en, origen, estado) "
                "VALUES (:inicio, :origen, 'en_curso')"
            ),
            {"inicio": inicio, "origen": str(origen)},
        )
        importacion_id = int(resultado.lastrowid)

    detalles: list[dict[str, Any]] = []
    total_filas = 0
    archivos = 0
    for tabla in TABLAS:
        try:
            detalle = _importar_tabla(tabla, origen)
        except Exception as exc:  # noqa: BLE001 - una tabla mala no detiene el resto
            detalle = {
                "tabla": tabla.nombre,
                "archivo": tabla.archivo,
                "filas": 0,
                "columnas": 0,
                "error": f"{type(exc).__name__}: {exc}",
                "advertencias": [],
            }
        detalles.append(detalle)
        total_filas += detalle["filas"]
        if detalle["filas"]:
            archivos += 1
        with db.conexion() as con:
            con.execute(
                text(
                    "INSERT INTO importacion_tablas "
                    "(importacion_id, tabla, filas, columnas, error) "
                    "VALUES (:id, :tabla, :filas, :columnas, :error)"
                ),
                {
                    "id": importacion_id,
                    "tabla": detalle["tabla"],
                    "filas": detalle["filas"],
                    "columnas": detalle["columnas"],
                    "error": " | ".join(detalle["advertencias"]) or detalle["error"],
                },
            )

    errores = [d for d in detalles if d["error"]]
    estado = "ok" if not errores else ("parcial" if archivos else "error")
    fin = datetime.now()
    resumen = (
        f"{archivos} archivos, {total_filas} filas, "
        f"{len(errores)} con error, {(fin - inicio).total_seconds():.1f} s"
    )
    with db.conexion() as con:
        con.execute(
            text(
                "UPDATE importaciones SET terminada_en = :fin, estado = :estado, "
                "tablas = :tablas, filas = :filas, archivos = :archivos, detalle = :detalle "
                "WHERE id = :id"
            ),
            {
                "fin": fin,
                "estado": estado,
                "tablas": len(detalles),
                "filas": total_filas,
                "archivos": archivos,
                "detalle": resumen,
                "id": importacion_id,
            },
        )

    return {
        "id": importacion_id,
        "estado": estado,
        "archivos": archivos,
        "tablas": len(detalles),
        "filas": total_filas,
        "segundos": round((fin - inicio).total_seconds(), 1),
        "detalle": detalles,
    }


def ultima_importacion() -> dict[str, Any] | None:
    cabecera = db.fila(
        "SELECT * FROM importaciones ORDER BY id DESC LIMIT 1"
    )
    if not cabecera:
        return None
    cabecera["tablas_detalle"] = db.filas(
        "SELECT tabla, filas, columnas, error FROM importacion_tablas "
        "WHERE importacion_id = :id ORDER BY id",
        {"id": cabecera["id"]},
    )
    return cabecera


def conteos() -> dict[str, int]:
    """Filas por tabla, para el panel de control."""
    from .db import escalar

    resultado: dict[str, int] = {}
    for tabla in TABLAS:
        try:
            resultado[tabla.nombre] = int(
                escalar(f"SELECT COUNT(*) FROM `{tabla.nombre}`") or 0
            )
        except Exception:  # noqa: BLE001 - tabla aún no importada
            resultado[tabla.nombre] = 0
    return resultado
