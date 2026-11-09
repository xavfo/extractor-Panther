"""Adaptador de facturación con QuFact.

Esta fase deja preparado el punto de integración, pero **no emite nada**: sin
`QUFACT_URL` y `QUFACT_TOKEN` configurados, `disponible()` devuelve ``False`` y
la interfaz muestra el aviso en lugar de intentar cobrar.

El contrato propuesto se documenta en `docs/QUFACT_INTEGRACION.md`. Se eligió un
endpoint JSON con token porque el visor es un sistema externo y no comparte la
sesión PHP de QuFact.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .config import AJUSTES


@dataclass(frozen=True)
class ResultadoFactura:
    ok: bool
    mensaje: str
    clave_acceso: str | None = None
    numero_autorizacion: str | None = None
    estado: str | None = None
    crudo: dict[str, Any] | None = None


def disponible() -> bool:
    return bool(AJUSTES.qufact_url and AJUSTES.qufact_token)


def _llamar(ruta: str, carga: dict[str, Any], segundos: int = 25) -> dict[str, Any]:
    peticion = urllib.request.Request(
        AJUSTES.qufact_url.rstrip("/") + ruta,
        data=json.dumps(carga).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {AJUSTES.qufact_token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(peticion, timeout=segundos) as respuesta:
        return json.loads(respuesta.read().decode("utf-8"))


def emitir_factura(datos: dict[str, Any]) -> ResultadoFactura:
    """Emite un comprobante a partir de un consumo del visor.

    ``datos`` debe traer: contribuyente (RUC), cliente, ítems (descripción,
    cantidad, precio, IVA) y la referencia del movimiento de Panther, para que
    QuFact pueda evitar duplicados por ``custom_uid``.
    """
    if not disponible():
        return ResultadoFactura(
            ok=False,
            mensaje="QuFact no está configurado (falta QUFACT_URL o QUFACT_TOKEN).",
        )
    try:
        respuesta = _llamar("/api/visor/emitir.php", datos)
    except urllib.error.HTTPError as exc:
        detalle = exc.read().decode("utf-8", errors="replace")[:500]
        return ResultadoFactura(ok=False, mensaje=f"QuFact respondió {exc.code}: {detalle}")
    except Exception as exc:  # noqa: BLE001 - se informa al operador
        return ResultadoFactura(ok=False, mensaje=f"No se pudo contactar a QuFact: {exc}")

    return ResultadoFactura(
        ok=bool(respuesta.get("success")),
        mensaje=str(respuesta.get("message") or ""),
        clave_acceso=respuesta.get("clave_acceso"),
        numero_autorizacion=respuesta.get("numero_autorizacion"),
        estado=respuesta.get("estado"),
        crudo=respuesta,
    )
