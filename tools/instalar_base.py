r"""Prepara la base MySQL del instalador y carga el respaldo con datos.

Se ejecuta desde `instalador\instalar.ps1`, pero también sirve a mano:

    python tools\instalar_base.py --sql sql\vetvisor_completo.sql

La contraseña de MySQL se toma de la variable `VETVISOR_DB_PASSWORD` para que no
quede escrita en la línea de comandos ni en el historial de la terminal.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import pymysql

_NOMBRE_VALIDO = re.compile(r"^[A-Za-z0-9_]+$")


def conectar(host: str, puerto: int, usuario: str, clave: str, base: str | None = None):
    return pymysql.connect(
        host=host,
        port=puerto,
        user=usuario,
        password=clave,
        database=base,
        charset="utf8mb4",
        autocommit=True,
        connect_timeout=8,
    )


def sentencias(ruta: Path):
    """Divide el respaldo de mysqldump en sentencias completas.

    mysqldump escribe cada INSERT en una sola línea y cierra cada sentencia con
    punto y coma al final de la línea; por eso alcanza con cortar ahí.
    """
    acumulado: list[str] = []
    with ruta.open(encoding="utf-8", errors="replace") as archivo:
        for linea in archivo:
            if not acumulado and (not linea.strip() or linea.lstrip().startswith("--")):
                continue
            acumulado.append(linea)
            if linea.rstrip().endswith(";"):
                texto = "".join(acumulado).strip()
                acumulado.clear()
                if texto:
                    yield texto
    resto = "".join(acumulado).strip()
    if resto:
        yield resto


def contar_tablas(con, base: str) -> int:
    with con.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s",
            (base,),
        )
        return int(cursor.fetchone()[0])


def cargar(host: str, puerto: int, usuario: str, clave: str, base: str, ruta: Path) -> int:
    con = conectar(host, puerto, usuario, clave, base)
    total = 0
    try:
        for numero, sentencia in enumerate(sentencias(ruta), start=1):
            try:
                with con.cursor() as cursor:
                    cursor.execute(sentencia)
            except Exception as exc:  # noqa: BLE001 - se informa la sentencia exacta
                resumen = " ".join(sentencia.split())[:180]
                raise RuntimeError(
                    f"Falló la sentencia #{numero}: {resumen}… → {exc}"
                ) from exc
            total = numero
    finally:
        con.close()
    return total


def main() -> int:
    analizador = argparse.ArgumentParser(description="Preparar la base e importar el respaldo")
    analizador.add_argument("--host", default="127.0.0.1")
    analizador.add_argument("--port", type=int, default=3307)
    analizador.add_argument("--user", default="root")
    analizador.add_argument("--password", default=None)
    analizador.add_argument("--name", default="vetvisor")
    analizador.add_argument("--sql", default="sql/vetvisor_completo.sql")
    analizador.add_argument(
        "--restaurar",
        action="store_true",
        help="Recargar el respaldo aunque la base ya tenga tablas",
    )
    argumentos = analizador.parse_args()

    clave = argumentos.password
    if clave is None:
        clave = os.getenv("VETVISOR_DB_PASSWORD", "")

    if not _NOMBRE_VALIDO.match(argumentos.name):
        print(f"Nombre de base inválido: {argumentos.name!r}", file=sys.stderr)
        return 2

    ruta = Path(argumentos.sql)
    if not ruta.exists():
        print(f"No existe el respaldo: {ruta}", file=sys.stderr)
        return 2

    try:
        servidor = conectar(argumentos.host, argumentos.port, argumentos.user, clave)
    except Exception as exc:  # noqa: BLE001
        print(f"No se pudo conectar a MySQL: {exc}", file=sys.stderr)
        return 3

    try:
        with servidor.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{argumentos.name}` "
                "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        tablas = contar_tablas(servidor, argumentos.name)
    finally:
        servidor.close()

    if tablas and not argumentos.restaurar:
        print(f"La base '{argumentos.name}' ya tiene {tablas} tablas; no se recarga.")
        print("Usa --restaurar para sobrescribirla con el respaldo.")
        return 0

    print(f"Cargando {ruta} en '{argumentos.name}'…")
    try:
        ejecutadas = cargar(
            argumentos.host, argumentos.port, argumentos.user, clave, argumentos.name, ruta
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Error al cargar: {exc}", file=sys.stderr)
        return 4

    comprobacion = conectar(
        argumentos.host, argumentos.port, argumentos.user, clave, argumentos.name
    )
    try:
        resumen = []
        with comprobacion.cursor() as cursor:
            for tabla, etiqueta in (
                ("TranAfiliado", "pacientes"),
                ("TranInformeMedico", "informes"),
                ("TranExamenes", "exámenes"),
                ("TranRegistroVacunas", "vacunas"),
            ):
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM `{tabla}`")
                    resumen.append(f"{cursor.fetchone()[0]} {etiqueta}")
                except Exception:  # noqa: BLE001 - tabla ausente
                    pass
        tablas_finales = contar_tablas(comprobacion, argumentos.name)
    finally:
        comprobacion.close()

    print(f"Listo: {ejecutadas} sentencias, {tablas_finales} tablas, {', '.join(resumen)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
