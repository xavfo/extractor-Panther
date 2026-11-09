"""Limpieza y conversión de los valores que vienen de Access/Panther.

Los XLSX traen texto correcto en UTF-8, pero con tres particularidades:

* los saltos de línea de Access quedan como ``_x000D_`` (a veces seguidos de un
  salto real, a veces solos);
* hay acentos descompuestos (``i`` + acento combinante) que hay que unificar a
  NFC para que las búsquedas encuentren «María» escrita de las dos formas;
* los vacíos llegan como ``nan``, cadena vacía, ``.`` o ``<empty>``.

Las conversiones devuelven ``None`` en vez de inventar un valor: si un importe o
una fecha no se puede interpretar, se guarda NULL y queda visible en el informe
de importación.
"""
from __future__ import annotations

import math
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

VACIOS = {"", "nan", "none", "null", "nat", "<empty>", "<na>"}

_FORMATOS_FECHA = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y",
    "%d-%m-%Y",
)

_RE_SALTO_ACCESS = re.compile(r"_x000[Dd]_")
_RE_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def es_vacio(valor: Any) -> bool:
    if valor is None:
        return True
    if isinstance(valor, float) and math.isnan(valor):
        return True
    if isinstance(valor, str) and valor.strip().lower() in VACIOS:
        return True
    return False


def texto(valor: Any) -> str | None:
    """Texto normalizado, o ``None`` si el origen está vacío."""
    if es_vacio(valor):
        return None
    if isinstance(valor, (datetime, date)):
        return valor.isoformat(sep=" ")
    if isinstance(valor, Decimal):
        texto_valor = format(valor, "f")
    elif isinstance(valor, float):
        texto_valor = format(valor, ".10g")
    else:
        texto_valor = str(valor)

    texto_valor = _RE_SALTO_ACCESS.sub("\n", texto_valor)
    texto_valor = texto_valor.replace("\r\n", "\n").replace("\r", "\n")
    texto_valor = _RE_CONTROL.sub("", texto_valor)
    texto_valor = unicodedata.normalize("NFC", texto_valor)
    texto_valor = texto_valor.strip()
    return texto_valor or None


def fecha(valor: Any) -> datetime | None:
    """Fecha/hora interpretable, o ``None``.

    ``00:00:00`` suelto (hora sin fecha) también devuelve ``None``: en Access
    significa «sin fecha», no el año cero.
    """
    if es_vacio(valor):
        return None
    if isinstance(valor, datetime):
        return valor
    if isinstance(valor, date):
        return datetime(valor.year, valor.month, valor.day)

    limpio = texto(valor)
    if not limpio or ":" == limpio.strip(":"):
        return None
    if re.fullmatch(r"\d{1,2}:\d{2}(:\d{2})?", limpio):
        return None

    for formato in _FORMATOS_FECHA:
        try:
            return datetime.strptime(limpio, formato)
        except ValueError:
            continue
    return None


def decimal(valor: Any) -> Decimal | None:
    if es_vacio(valor):
        return None
    if isinstance(valor, Decimal):
        return valor
    limpio = texto(valor)
    if limpio is None:
        return None
    limpio = limpio.replace("$", "").replace(" ", "")
    # Formato ecuatoriano: 1.234,56 cuando hay coma y punto juntos.
    if "," in limpio and "." in limpio:
        limpio = limpio.replace(".", "").replace(",", ".")
    elif "," in limpio:
        limpio = limpio.replace(",", ".")
    try:
        return Decimal(limpio)
    except InvalidOperation:
        return None


def entero(valor: Any) -> int | None:
    if es_vacio(valor):
        return None
    if isinstance(valor, bool):
        return int(valor)
    if isinstance(valor, (int, float, Decimal)):
        return int(valor)
    limpio = texto(valor)
    if limpio is None:
        return None
    limpio = limpio.lower()
    if limpio in {"true", "verdadero", "si", "sí"}:
        return 1
    if limpio in {"false", "falso", "no"}:
        return 0
    try:
        return int(Decimal(limpio))
    except (InvalidOperation, ValueError):
        return None


def booleano(valor: Any) -> int | None:
    resultado = entero(valor)
    if resultado is None:
        return None
    return 1 if resultado else 0


def convertir(valor: Any, tipo_sql: str) -> Any:
    """Convierte un valor de Excel al tipo de la columna destino."""
    if tipo_sql.startswith("DATETIME"):
        return fecha(valor)
    if tipo_sql.startswith("DECIMAL"):
        return decimal(valor)
    if tipo_sql.startswith("TINYINT"):
        return booleano(valor)
    if tipo_sql.startswith("INT"):
        return entero(valor)
    return texto(valor)


def nombre_columna_legible(columna: str) -> str:
    """Etiqueta para el navegador de tablas (no toca el nombre real)."""
    especiales = {
        "iCodPaciente": "Código de paciente",
        "vchNombrePaciente": "Nombre del paciente",
        "vchNombre": "Nombre",
        "vchPaterno": "Apellido paterno",
        "vchMaterno": "Apellido materno",
        "vchTelefono": "Teléfono",
        "vchCorreo": "Correo",
        "dtFecha": "Fecha",
        "dtFecNacimiento": "Fecha de nacimiento",
        "vchSexo": "Sexo",
        "vchRaza": "Raza",
        "vchColor": "Color",
        "vchEspecie": "Especie",
        "vchObservaciones": "Observaciones",
        "vchMotivo": "Motivo",
        "vchNota": "Nota clínica",
        "vchMedico": "Médico",
        "vchNombreMedico": "Médico",
        "iCodEspecie": "Código de especie",
    }
    if columna in especiales:
        return especiales[columna]
    return columna
