"""Autenticación y sesiones.

Contraseñas con PBKDF2-SHA256 (sal por usuario, 260 000 iteraciones). La cookie
de sesión va firmada con `SECRETO_SESION` y es `SameSite=Lax`, suficiente para
una red interna sin HTTPS. Si el visor se publica fuera del local, hay que
poner HTTPS delante y activar `https_only`.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from datetime import datetime
from typing import Any

from starlette.requests import Request

from . import db
from .config import AJUSTES

ITERACIONES = 260_000
_MAX_INTENTOS = 8
_VENTANA_SEGUNDOS = 300
_intentos: dict[str, list[float]] = {}


def hash_password(password: str) -> str:
    sal = os.urandom(16)
    derivada = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), sal, ITERACIONES
    )
    return "pbkdf2_sha256${}${}${}".format(
        ITERACIONES,
        base64.b64encode(sal).decode("ascii"),
        base64.b64encode(derivada).decode("ascii"),
    )


def verificar_password(password: str, guardado: str) -> bool:
    try:
        algoritmo, iteraciones, sal_b64, esperado_b64 = guardado.split("$")
        if algoritmo != "pbkdf2_sha256":
            return False
        sal = base64.b64decode(sal_b64)
        esperado = base64.b64decode(esperado_b64)
        derivada = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), sal, int(iteraciones)
        )
        return hmac.compare_digest(derivada, esperado)
    except (ValueError, TypeError):
        return False


def crear_admin_si_falta() -> bool:
    """Crea el administrador inicial si la tabla está vacía."""
    total = int(db.escalar("SELECT COUNT(*) FROM usuarios") or 0)
    if total:
        return False
    db.ejecutar(
        "INSERT INTO usuarios (usuario, nombre, correo, password_hash, rol, activo, creado_en) "
        "VALUES (:usuario, :nombre, NULL, :hash, 'admin', 1, :creado)",
        {
            "usuario": AJUSTES.admin_usuario,
            "nombre": "Administrador",
            "hash": hash_password(AJUSTES.admin_password),
            "creado": datetime.now(),
        },
    )
    return True


def autenticar(usuario: str, password: str) -> dict[str, Any] | None:
    registro = db.fila(
        "SELECT id, usuario, nombre, correo, password_hash, rol, activo "
        "FROM usuarios WHERE usuario = :usuario",
        {"usuario": usuario.strip()},
    )
    if not registro or not registro["activo"]:
        return None
    if not verificar_password(password, registro["password_hash"]):
        return None

    db.ejecutar(
        "UPDATE usuarios SET ultimo_acceso = :ahora WHERE id = :id",
        {"ahora": datetime.now(), "id": registro["id"]},
    )
    return {
        "id": registro["id"],
        "usuario": registro["usuario"],
        "nombre": registro["nombre"],
        "rol": registro["rol"],
    }


def usuario_sesion(request: Request) -> dict[str, Any] | None:
    datos = request.session.get("usuario")
    if not isinstance(datos, dict) or not datos.get("id"):
        return None
    return datos


def cerrar_sesion(request: Request) -> None:
    request.session.clear()


def permitir_intento(clave: str) -> bool:
    ahora = time.time()
    marcas = [marca for marca in _intentos.get(clave, []) if ahora - marca < _VENTANA_SEGUNDOS]
    _intentos[clave] = marcas
    return len(marcas) < _MAX_INTENTOS


def registrar_fallo(clave: str) -> None:
    _intentos.setdefault(clave, []).append(time.time())


def limpiar_intentos(clave: str) -> None:
    _intentos.pop(clave, None)


def listar_usuarios() -> list[dict[str, Any]]:
    return db.filas(
        "SELECT id, usuario, nombre, correo, rol, activo, creado_en, ultimo_acceso "
        "FROM usuarios ORDER BY nombre"
    )
