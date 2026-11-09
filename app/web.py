"""Piezas compartidas de la capa web: plantillas, filtros y contexto."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi.templating import Jinja2Templates

from . import auth
from .campos import etiqueta as _etiqueta_campo
from .config import RAIZ

plantillas = Jinja2Templates(directory=str(RAIZ / "app" / "templates"))


def _como_fecha(valor: Any, formato: str = "%d/%m/%Y") -> str:
    if valor in (None, ""):
        return "—"
    if isinstance(valor, str):
        for plantilla in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                valor = datetime.strptime(valor, plantilla)
                break
            except ValueError:
                continue
        else:
            return valor
    if isinstance(valor, (datetime, date)):
        return valor.strftime(formato)
    return str(valor)


def _fecha(valor: Any) -> str:
    return _como_fecha(valor, "%d/%m/%Y")


def _fecha_hora(valor: Any) -> str:
    return _como_fecha(valor, "%d/%m/%Y %H:%M")


def _moneda(valor: Any) -> str:
    if valor in (None, ""):
        return "—"
    try:
        numero = Decimal(str(valor))
    except Exception:  # noqa: BLE001 - se muestra el valor crudo
        return str(valor)
    entero, decimales = f"{numero:,.2f}".split(".")
    return f"$ {entero.replace(',', '.')},{decimales}"


def _numero(valor: Any, decimales: int = 2) -> str:
    if valor in (None, ""):
        return "—"
    try:
        numero = float(str(valor))
    except ValueError:
        return str(valor)
    entero, parte_decimal = f"{numero:,.{decimales}f}".split(".")
    return f"{entero.replace(',', '.')},{parte_decimal}"


def _edad(nacimiento: Any) -> str:
    if not nacimiento:
        return "—"
    if isinstance(nacimiento, str):
        nacimiento = _como_fecha(nacimiento, "%Y-%m-%d")
        try:
            nacimiento = datetime.strptime(nacimiento, "%Y-%m-%d")
        except ValueError:
            return "—"
    if isinstance(nacimiento, datetime):
        nacimiento = nacimiento.date()
    if not isinstance(nacimiento, date):
        return "—"
    hoy = date.today()
    meses = (hoy.year - nacimiento.year) * 12 + hoy.month - nacimiento.month
    if hoy.day < nacimiento.day:
        meses -= 1
    if meses < 0:
        return "—"
    if meses < 1:
        dias = (hoy - nacimiento).days
        return f"{dias} día{'s' if dias != 1 else ''}"
    if meses < 24:
        return f"{meses} mes{'es' if meses != 1 else ''}"
    anos, resto = divmod(meses, 12)
    if resto:
        return f"{anos} años {resto} m"
    return f"{anos} años"


def _valor(valor: Any) -> str:
    if valor is None:
        return "—"
    if isinstance(valor, str):
        limpio = valor.strip()
        if not limpio or limpio in {".", "-", "--"}:
            return "—"
        return limpio
    return str(valor)


def _si_no(valor: Any) -> str:
    if valor in (None, ""):
        return "—"
    texto = str(valor).strip().lower()
    return "Sí" if texto in {"1", "true", "si", "sí", "verdadero"} else "No"


def _corto(valor: Any, largo: int = 90) -> str:
    if valor in (None, ""):
        return "—"
    texto = str(valor).replace("\n", " ").strip()
    if len(texto) <= largo:
        return texto
    return texto[: largo - 1].rstrip() + "…"


def _iniciales(valor: Any) -> str:
    if not valor:
        return "?"
    partes = [parte for parte in str(valor).split() if parte]
    if not partes:
        return "?"
    if len(partes) == 1:
        return partes[0][:2].upper()
    return (partes[0][0] + partes[-1][0]).upper()


def _limpio(valor: Any) -> str:
    """Panther usa ``.`` y ``-`` como «sin dato»; aquí se vuelven cadena vacía."""
    if valor is None:
        return ""
    texto = str(valor).strip()
    return "" if texto in {"", ".", "-", "--", "None", "nan"} else texto


def _medida(valor: Any, sufijo: str = "") -> str:
    """Signo vital: el cero de Panther significa «no se tomó»."""
    if valor in (None, ""):
        return "—"
    try:
        numero = Decimal(str(valor))
    except Exception:  # noqa: BLE001 - valores como «120/80»
        return f"{valor} {sufijo}".strip()
    if numero == 0:
        return "—"
    if numero == numero.to_integral_value():
        texto = f"{int(numero):,}".replace(",", ".")
    else:
        texto = _numero(valor, 2)
    return f"{texto} {sufijo}".strip()


plantillas.env.filters.update(
    {
        "fecha": _fecha,
        "fecha_hora": _fecha_hora,
        "moneda": _moneda,
        "numero": _numero,
        "edad": _edad,
        "valor": _valor,
        "si_no": _si_no,
        "corto": _corto,
        "iniciales": _iniciales,
        "limpio": _limpio,
        "medida": _medida,
        "campo": _etiqueta_campo,
    }
)


def contexto(request: Any, **extra: Any) -> dict[str, Any]:
    datos: dict[str, Any] = {
        "request": request,
        "usuario": auth.usuario_sesion(request),
        "ruta": request.url.path,
        "mensaje": request.query_params.get("mensaje"),
        "tipo_mensaje": request.query_params.get("tipo", "ok"),
    }
    datos.update(extra)
    return datos
