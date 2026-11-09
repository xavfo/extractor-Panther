"""Crea un usuario o restablece su contraseña desde la terminal.

Uso:
    .\\.venv\\Scripts\\python.exe tools\\crear_admin.py
    .\\.venv\\Scripts\\python.exe tools\\crear_admin.py --usuario admin --rol admin
"""
from __future__ import annotations

import argparse
import getpass
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app import auth, db, esquema  # noqa: E402


def main() -> int:
    analizador = argparse.ArgumentParser(description="Crear o actualizar un usuario")
    analizador.add_argument("--usuario", default="admin")
    analizador.add_argument("--nombre", default="Administrador")
    analizador.add_argument("--correo", default=None)
    analizador.add_argument("--rol", default="admin", choices=["admin", "veterinario", "recepcion"])
    argumentos = analizador.parse_args()

    esquema.asegurar_tablas_propias()

    existente = db.fila(
        "SELECT id FROM usuarios WHERE usuario = :usuario",
        {"usuario": argumentos.usuario},
    )
    if existente:
        respuesta = input(
            f"El usuario {argumentos.usuario!r} ya existe. ¿Restablecer su contraseña? [s/N] "
        )
        if respuesta.strip().lower() not in {"s", "si", "sí"}:
            print("Sin cambios.")
            return 0

    password = getpass.getpass("Contraseña nueva: ")
    if len(password) < 8:
        print("La contraseña debe tener al menos 8 caracteres.")
        return 1
    if password != getpass.getpass("Repite la contraseña: "):
        print("Las contraseñas no coinciden.")
        return 1

    if existente:
        db.ejecutar(
            "UPDATE usuarios SET password_hash = :hash, rol = :rol, activo = 1 WHERE id = :id",
            {"hash": auth.hash_password(password), "rol": argumentos.rol, "id": existente["id"]},
        )
        print(f"Contraseña actualizada para {argumentos.usuario!r}.")
    else:
        db.ejecutar(
            "INSERT INTO usuarios (usuario, nombre, correo, password_hash, rol, activo, creado_en) "
            "VALUES (:usuario, :nombre, :correo, :hash, :rol, 1, :creado)",
            {
                "usuario": argumentos.usuario,
                "nombre": argumentos.nombre,
                "correo": argumentos.correo,
                "hash": auth.hash_password(password),
                "rol": argumentos.rol,
                "creado": datetime.now(),
            },
        )
        print(f"Usuario {argumentos.usuario!r} creado con rol {argumentos.rol!r}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
