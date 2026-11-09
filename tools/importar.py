"""Importa los XLSX de Panther a MySQL desde la terminal.

Uso:
    .\\.venv\\Scripts\\python.exe tools\\importar.py
    .\\.venv\\Scripts\\python.exe tools\\importar.py --carpeta "D:\\export panther"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app import importador  # noqa: E402


def main() -> int:
    analizador = argparse.ArgumentParser(description="Importar la exportación de Panther")
    analizador.add_argument("--carpeta", help="Carpeta con los XLSX (por defecto .src)")
    argumentos = analizador.parse_args()

    carpeta = Path(argumentos.carpeta) if argumentos.carpeta else None
    resultado = importador.importar(carpeta)

    print(f"Importación #{resultado['id']}: {resultado['estado']}")
    print(f"  archivos: {resultado['archivos']}   filas: {resultado['filas']}   "
          f"tiempo: {resultado['segundos']} s")
    for detalle in resultado["detalle"]:
        marca = "ERROR" if detalle["error"] else "ok"
        print(f"  [{marca:5}] {detalle['tabla']:<28} {detalle['filas']:>6} filas")
        for advertencia in detalle["advertencias"]:
            print(f"          · {advertencia}")
        if detalle["error"]:
            print(f"          · {detalle['error']}")
    return 0 if resultado["estado"] != "error" else 1


if __name__ == "__main__":
    raise SystemExit(main())
