"""Campos de la ficha que el visor permite corregir.

La lista es explícita a propósito: solo se pueden modificar datos de contacto,
identificación y observaciones. Nada de fechas, códigos ni importes, que son
los que sostienen la historia clínica y la facturación.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Campo:
    nombre: str
    etiqueta: str
    grupo: str
    tipo: str = "texto"  # texto | area | tel | correo
    maximo: int = 255
    ayuda: str = ""


GRUPOS: tuple[str, ...] = ("Paciente", "Propietario", "Notas clínicas")

CAMPOS_PACIENTE: tuple[Campo, ...] = (
    Campo("vchNombrePaciente", "Nombre del paciente", "Paciente"),
    Campo("vchRaza", "Raza", "Paciente"),
    Campo("vchColor", "Color", "Paciente"),
    Campo("vchNombre", "Nombre del propietario", "Propietario"),
    Campo("vchPaterno", "Apellido paterno", "Propietario"),
    Campo("vchMaterno", "Apellido materno", "Propietario"),
    Campo("vchTelefono", "Teléfono", "Propietario", "tel", 30),
    Campo("vchTelefono2", "Teléfono alterno", "Propietario", "tel", 30),
    Campo("vchCorreo", "Correo electrónico", "Propietario", "correo"),
    Campo("vchCorreo2", "Correo alterno", "Propietario", "correo"),
    Campo("vchDireccion", "Dirección", "Propietario"),
    Campo("vchColonia", "Sector o colonia", "Propietario"),
    Campo("vchCiudad", "Ciudad", "Propietario"),
    Campo("vchRFC", "Identificación", "Propietario", "texto", 40),
    Campo(
        "vchObservaciones",
        "Observaciones",
        "Notas clínicas",
        "area",
        4000,
        "Descripción general registrada en Panther.",
    ),
)

CAMPOS_POR_NOMBRE: dict[str, Campo] = {campo.nombre: campo for campo in CAMPOS_PACIENTE}


def etiqueta(nombre: str | None) -> str:
    if not nombre:
        return "—"
    campo = CAMPOS_POR_NOMBRE.get(nombre)
    return campo.etiqueta if campo else nombre
