"""Edición de la ficha del paciente y notas internas.

Regla central: **el dato de Panther nunca se sobrescribe**. Cada cambio se
guarda como una corrección por campo en la tabla `correcciones`, y las consultas
muestran la corrección por encima del valor original (`COALESCE` en la vista
`pacientes_vista`). Así se puede volver al original en cualquier momento y se
conserva la trazabilidad de quién cambió qué.

Todas las operaciones escriben en `auditoria` dentro de la misma transacción.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from sqlalchemy import text

from . import db
from .campos import CAMPOS_PACIENTE, CAMPOS_POR_NOMBRE

_RE_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MAX_NOTA = 4000
_MIN_NOTA = 3
_VACIOS_ORIGEN = {".", "-", "--"}


def _limpiar(valor: Any) -> str:
    if valor is None:
        return ""
    texto = str(valor).replace("\r\n", "\n").replace("\r", "\n")
    texto = "".join(caracter for caracter in texto if caracter == "\n" or caracter >= " ")
    return texto.strip()


def validar(valores: dict[str, str]) -> dict[str, str]:
    """Errores por campo. Un campo vacío es válido: significa «dejarlo vacío»."""
    errores: dict[str, str] = {}
    for campo in CAMPOS_PACIENTE:
        if campo.nombre not in valores:
            continue
        valor = _limpiar(valores[campo.nombre])
        if len(valor) > campo.maximo:
            errores[campo.nombre] = f"Máximo {campo.maximo} caracteres."
        elif (
            campo.tipo == "correo"
            and valor
            and valor not in _VACIOS_ORIGEN
            and not _RE_CORREO.match(valor)
        ):
            errores[campo.nombre] = "El correo no tiene un formato válido."
    return errores


def _auditar(
    con,
    usuario: dict[str, Any],
    tabla: str,
    clave: str,
    accion: str,
    campo: str | None,
    anterior: Any,
    nuevo: Any,
    ip: str,
) -> None:
    con.execute(
        text(
            "INSERT INTO auditoria (usuario_id, usuario, tabla, clave, accion, campo, "
            "valor_anterior, valor_nuevo, fecha, ip) "
            "VALUES (:uid, :usuario, :tabla, :clave, :accion, :campo, "
            ":anterior, :nuevo, :fecha, :ip)"
        ),
        {
            "uid": usuario.get("id"),
            "usuario": usuario.get("usuario"),
            "tabla": tabla,
            "clave": clave,
            "accion": accion,
            "campo": campo,
            "anterior": None if anterior is None else str(anterior),
            "nuevo": None if nuevo is None else str(nuevo),
            "fecha": datetime.now(),
            "ip": ip,
        },
    )


def correcciones_de(codigo: str) -> dict[str, dict[str, Any]]:
    filas = db.filas(
        "SELECT id, campo, valor, valor_original, usuario, motivo, creada_en, "
        "actualizada_en FROM correcciones "
        "WHERE tabla = 'TranAfiliado' AND clave = :clave",
        {"clave": codigo},
    )
    return {fila["campo"]: fila for fila in filas}


def valores_base(codigo: str) -> dict[str, Any]:
    """Valores tal como están en la tabla de Panther (sin correcciones)."""
    return db.fila(
        "SELECT * FROM TranAfiliado WHERE iCodPaciente = :codigo "
        "ORDER BY dtFecha DESC LIMIT 1",
        {"codigo": codigo},
    ) or {}


def guardar_correcciones(
    usuario: dict[str, Any],
    codigo: str,
    valores: dict[str, str],
    motivo: str,
    ip: str,
) -> list[dict[str, Any]]:
    """Guarda los cambios de una ficha. Devuelve la lista de cambios aplicados."""
    ahora = datetime.now()
    motivo = _limpiar(motivo)[:255] or None
    cambios: list[dict[str, Any]] = []

    with db.conexion() as con:
        base = con.execute(
            text(
                "SELECT * FROM TranAfiliado WHERE iCodPaciente = :codigo "
                "ORDER BY dtFecha DESC LIMIT 1"
            ),
            {"codigo": codigo},
        ).mappings().first()
        if not base:
            raise ValueError("El paciente no existe en la base local.")
        base = dict(base)

        existentes = {
            fila["campo"]: dict(fila)
            for fila in con.execute(
                text(
                    "SELECT * FROM correcciones "
                    "WHERE tabla = 'TranAfiliado' AND clave = :clave"
                ),
                {"clave": codigo},
            ).mappings()
        }

        for campo in CAMPOS_PACIENTE:
            if campo.nombre not in valores:
                continue
            nuevo = _limpiar(valores[campo.nombre])
            original = "" if base.get(campo.nombre) is None else str(base[campo.nombre])
            correccion = existentes.get(campo.nombre)
            vigente = correccion["valor"] if correccion else original

            if nuevo == (vigente or ""):
                continue

            if nuevo == original:
                if not correccion:
                    continue
                con.execute(
                    text("DELETE FROM correcciones WHERE id = :id"),
                    {"id": correccion["id"]},
                )
                _auditar(con, usuario, "TranAfiliado", codigo, "restaurar",
                         campo.nombre, vigente, original, ip)
                cambios.append({
                    "campo": campo.etiqueta,
                    "anterior": vigente,
                    "nuevo": original,
                    "accion": "restaurar",
                })
                continue

            accion = "actualizar" if correccion else "crear"
            con.execute(
                text(
                    "INSERT INTO correcciones "
                    "(tabla, clave, campo, valor, valor_original, usuario_id, usuario, "
                    "motivo, creada_en, actualizada_en) "
                    "VALUES ('TranAfiliado', :clave, :campo, :valor, :original, "
                    ":uid, :usuario, :motivo, :ahora, :ahora) "
                    "ON DUPLICATE KEY UPDATE valor = VALUES(valor), "
                    "valor_original = VALUES(valor_original), usuario_id = VALUES(usuario_id), "
                    "usuario = VALUES(usuario), motivo = VALUES(motivo), "
                    "actualizada_en = VALUES(actualizada_en)"
                ),
                {
                    "clave": codigo,
                    "campo": campo.nombre,
                    "valor": nuevo,
                    "original": original,
                    "uid": usuario.get("id"),
                    "usuario": usuario.get("usuario"),
                    "motivo": motivo,
                    "ahora": ahora,
                },
            )
            _auditar(con, usuario, "TranAfiliado", codigo, accion,
                     campo.nombre, vigente, nuevo, ip)
            cambios.append({
                "campo": campo.etiqueta,
                "anterior": vigente,
                "nuevo": nuevo,
                "accion": accion,
            })

    return cambios


def quitar_correccion(
    usuario: dict[str, Any], codigo: str, campo: str, ip: str
) -> bool:
    """Restaura el valor original de un campo. Devuelve si había algo que quitar."""
    if campo not in CAMPOS_POR_NOMBRE:
        raise ValueError("Campo no editable.")

    with db.conexion() as con:
        correccion = con.execute(
            text(
                "SELECT * FROM correcciones WHERE tabla = 'TranAfiliado' "
                "AND clave = :clave AND campo = :campo"
            ),
            {"clave": codigo, "campo": campo},
        ).mappings().first()
        if not correccion:
            return False

        base = con.execute(
            text(
                "SELECT * FROM TranAfiliado WHERE iCodPaciente = :codigo "
                "ORDER BY dtFecha DESC LIMIT 1"
            ),
            {"codigo": codigo},
        ).mappings().first()
        actual = ""
        if base and base.get(campo) is not None:
            actual = str(base[campo])

        con.execute(
            text("DELETE FROM correcciones WHERE id = :id"),
            {"id": correccion["id"]},
        )
        _auditar(con, usuario, "TranAfiliado", codigo, "restaurar",
                 campo, correccion["valor"], actual, ip)
    return True


def listar_notas(codigo: str) -> list[dict[str, Any]]:
    return db.filas(
        "SELECT id, nota, usuario_id, usuario, creada_en FROM notas_paciente "
        "WHERE iCodPaciente = :codigo ORDER BY creada_en DESC, id DESC",
        {"codigo": codigo},
    )


def crear_nota(
    usuario: dict[str, Any], codigo: str, texto_nota: str, ip: str
) -> int:
    texto_nota = _limpiar(texto_nota)
    if len(texto_nota) < _MIN_NOTA:
        raise ValueError("La nota es demasiado corta.")
    if len(texto_nota) > _MAX_NOTA:
        raise ValueError(f"La nota supera los {_MAX_NOTA} caracteres.")

    with db.conexion() as con:
        resultado = con.execute(
            text(
                "INSERT INTO notas_paciente (iCodPaciente, nota, usuario_id, usuario, creada_en) "
                "VALUES (:codigo, :nota, :uid, :usuario, :ahora)"
            ),
            {
                "codigo": codigo,
                "nota": texto_nota,
                "uid": usuario.get("id"),
                "usuario": usuario.get("usuario"),
                "ahora": datetime.now(),
            },
        )
        _auditar(con, usuario, "notas_paciente", codigo, "nota_crear",
                 None, None, texto_nota, ip)
        return int(resultado.lastrowid)


def eliminar_nota(
    usuario: dict[str, Any], codigo: str, nota_id: int, ip: str
) -> bool:
    with db.conexion() as con:
        nota = con.execute(
            text(
                "SELECT id, iCodPaciente, nota, usuario_id FROM notas_paciente "
                "WHERE id = :id"
            ),
            {"id": nota_id},
        ).mappings().first()
        if not nota or nota["iCodPaciente"] != codigo:
            return False

        es_autor = nota["usuario_id"] == usuario.get("id")
        es_admin = usuario.get("rol") == "admin"
        if not (es_autor or es_admin):
            raise PermissionError("Solo el autor o un administrador puede eliminar la nota.")

        con.execute(text("DELETE FROM notas_paciente WHERE id = :id"), {"id": nota_id})
        _auditar(con, usuario, "notas_paciente", codigo, "nota_eliminar",
                 None, nota["nota"], "", ip)
    return True
