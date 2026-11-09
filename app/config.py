"""Configuración del visor veterinario.

Todo lo que cambia entre el equipo de desarrollo y el servidor del local se lee
del entorno (`.env`), para que el mismo código corra en local y en la LAN.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")


def _texto(nombre: str, por_defecto: str) -> str:
    valor = os.getenv(nombre)
    return valor.strip() if valor and valor.strip() else por_defecto


def _entero(nombre: str, por_defecto: int) -> int:
    try:
        return int(os.getenv(nombre, ""))
    except (TypeError, ValueError):
        return por_defecto


def _booleano(nombre: str, por_defecto: bool = False) -> bool:
    valor = os.getenv(nombre, "").strip().lower()
    if not valor:
        return por_defecto
    return valor in {"1", "true", "si", "sí", "yes", "on"}


@dataclass(frozen=True)
class Ajustes:
    db_host: str
    db_puerto: int
    db_nombre: str
    db_usuario: str
    db_password: str
    secreto_sesion: str
    admin_usuario: str
    admin_password: str
    ruta_exportacion: Path
    ruta_almacen: Path
    qufact_url: str
    qufact_token: str

    @property
    def base_datos_url(self) -> str:
        credencial = self.db_usuario
        if self.db_password:
            credencial += f":{quote_plus(self.db_password)}"
        return (
            f"mysql+pymysql://{credencial}@{self.db_host}:{self.db_puerto}"
            f"/{self.db_nombre}?charset=utf8mb4"
        )

    @property
    def base_datos_sin_nombre(self) -> str:
        credencial = self.db_usuario
        if self.db_password:
            credencial += f":{quote_plus(self.db_password)}"
        return f"mysql+pymysql://{credencial}@{self.db_host}:{self.db_puerto}/?charset=utf8mb4"


def cargar_ajustes() -> Ajustes:
    return Ajustes(
        db_host=_texto("DB_HOST", "127.0.0.1"),
        db_puerto=_entero("DB_PORT", 3307),
        db_nombre=_texto("DB_NAME", "vetvisor"),
        db_usuario=_texto("DB_USER", "root"),
        db_password=os.getenv("DB_PASSWORD", ""),
        secreto_sesion=_texto("SECRETO_SESION", "cambiar-esta-clave-en-produccion"),
        admin_usuario=_texto("ADMIN_USUARIO", "admin"),
        admin_password=os.getenv("ADMIN_PASSWORD", "Vetvisor2026*"),
        ruta_exportacion=Path(_texto("RUTA_EXPORTACION", str(RAIZ / ".src"))),
        ruta_almacen=Path(_texto("RUTA_ALMACEN", str(RAIZ / "storage" / "documentos"))),
        qufact_url=_texto("QUFACT_URL", "http://127.0.0.1:8099"),
        qufact_token=os.getenv("QUFACT_TOKEN", ""),
    )


AJUSTES = cargar_ajustes()
