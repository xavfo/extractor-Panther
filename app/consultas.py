"""Consultas del visor.

Todo el SQL vive aquí para que las plantillas no lo mezclen con HTML y para
poder revisar de un vistazo qué se lee de cada tabla de Panther.
"""
from __future__ import annotations

from typing import Any

from . import db
from .esquema import TABLAS, POR_NOMBRE

POR_PAGINA = 25


def _patron(busqueda: str) -> str:
    limpio = busqueda.strip()
    limpio = limpio.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{limpio}%"


def resumen() -> dict[str, int]:
    conteos = {
        "pacientes": "TranAfiliado",
        "informes": "TranInformeMedico",
        "examenes": "TranExamenes",
        "vacunas": "TranRegistroVacunas",
        "citas": "TranCalendario",
    }
    resultado = {clave: 0 for clave in conteos}
    for clave, tabla in conteos.items():
        try:
            resultado[clave] = int(db.escalar(f"SELECT COUNT(*) FROM `{tabla}`") or 0)
        except Exception:  # noqa: BLE001 - tabla no importada todavía
            resultado[clave] = 0
    try:
        resultado["documentos"] = int(db.escalar("SELECT COUNT(*) FROM documentos") or 0)
    except Exception:  # noqa: BLE001
        resultado["documentos"] = 0
    return resultado


# --------------------------------------------------------------------------
# Pacientes
# --------------------------------------------------------------------------

_FILTRO_PACIENTE = """
    (:q = '' OR a.vchNombrePaciente LIKE :like
     OR CONCAT_WS(' ', a.vchNombre, a.vchPaterno, a.vchMaterno) LIKE :like
     OR a.vchTelefono LIKE :like OR a.vchCorreo LIKE :like
     OR a.chCodPaciente LIKE :like OR a.iNoPaciente LIKE :like)
"""


def listar_pacientes(busqueda: str = "", pagina: int = 1) -> dict[str, Any]:
    busqueda = busqueda.strip()
    parametros = {"q": busqueda, "like": _patron(busqueda)}
    total = int(db.escalar(
        f"SELECT COUNT(*) FROM TranAfiliado a WHERE {_FILTRO_PACIENTE}",
        parametros,
    ) or 0)
    pagina = max(1, pagina)
    desplazamiento = (pagina - 1) * POR_PAGINA
    registros = db.filas(
        f"""
        SELECT a.iCodPaciente, a.chCodPaciente, a.iNoPaciente, a.vchNombrePaciente,
               a.vchSexo, a.vchRaza, a.vchColor, a.dtFecNacimiento, a.iCodEspecie,
               a.vchNombre, a.vchPaterno, a.vchMaterno, a.vchTelefono, a.vchCorreo,
               a.bActivo, a.bCastrado, e.vchEspecie,
               (SELECT MAX(i.dtFechaInformeMedico) FROM TranInformeMedico i
                 WHERE i.iCodPaciente = a.iCodPaciente) AS ultima_visita
        FROM TranAfiliado a
        LEFT JOIN CatEspecies e ON e.iCodEspecie = a.iCodEspecie
        WHERE {_FILTRO_PACIENTE}
        ORDER BY a.vchNombrePaciente
        LIMIT :limite OFFSET :desplazamiento
        """,
        {**parametros, "limite": POR_PAGINA, "desplazamiento": desplazamiento},
    )
    return {
        "registros": registros,
        "total": total,
        "pagina": pagina,
        "por_pagina": POR_PAGINA,
        "paginas": max(1, -(-total // POR_PAGINA)),
        "busqueda": busqueda,
    }


def obtener_paciente(codigo: str) -> dict[str, Any] | None:
    paciente = db.fila(
        """
        SELECT a.*, e.vchEspecie
        FROM TranAfiliado a
        LEFT JOIN CatEspecies e ON e.iCodEspecie = a.iCodEspecie
        WHERE a.iCodPaciente = :codigo
        ORDER BY a.dtFecha DESC
        LIMIT 1
        """,
        {"codigo": codigo},
    )
    if not paciente:
        return None
    return paciente


def historia_paciente(codigo: str) -> dict[str, list[dict[str, Any]]]:
    parametros = {"codigo": codigo}
    return {
        "informes": db.filas(
            """
            SELECT iCodInformeMedico, vchNumInformeMedico, dtFechaInformeMedico,
                   vchMotivo, sDiagnosticoPresuntivo, vchMedico, dPeso, dTemperatura,
                   iEstatus
            FROM TranInformeMedico
            WHERE iCodPaciente = :codigo
            ORDER BY dtFechaInformeMedico DESC, iCodInformeMedico DESC
            """,
            parametros,
        ),
        "vacunas": db.filas(
            """
            SELECT iCodVacuna, dtFecha, sVacunaAplicada, sNumeroLote, sProximaVacuna,
                   dtFechaProgramada, dPeso
            FROM TranRegistroVacunas
            WHERE iCodPaciente = :codigo
            ORDER BY dtFecha DESC
            """,
            parametros,
        ),
        "desparasitaciones": db.filas(
            """
            SELECT iCodDesparacitacion, dtFecha, sProductoAplicado, dtFechaProxima,
                   sObservaciones, dPeso
            FROM TranDesparacitacion
            WHERE iCodPaciente = :codigo
            ORDER BY dtFecha DESC
            """,
            parametros,
        ),
        "examenes": db.filas(
            """
            SELECT iCodTranExamen, dtFecha, vchDescripcion, vchObservaciones,
                   vchNombreArchivo, tiEstatus
            FROM TranExamenes
            WHERE iCodPaciente = :codigo
            ORDER BY dtFecha DESC
            """,
            parametros,
        ),
        "cirugias": db.filas(
            """
            SELECT iCodCirugia, dtFecha, dtFechaRevision, vchDescripcion,
                   vchObservaciones, vchMedico
            FROM TranCirugias
            WHERE iCodPaciente = :codigo
            ORDER BY dtFecha DESC
            """,
            parametros,
        ),
        "hospitalizacion": db.filas(
            """
            SELECT iCodTranHospitalizacion, dtFechaIngreso, dtFechaSalida,
                   vchMotivoIngreso, vchDiagnostico, vchMedico, iNumJaula, tiEstatus
            FROM TranHospitalizacion
            WHERE iCodPaciente = :codigo
            ORDER BY dtFechaIngreso DESC
            """,
            parametros,
        ),
        "cuenta": db.filas(
            """
            SELECT iCodCuentaCliente, dtFecha, vchServicio, dPrecioMenudeo, dCantidad,
                   dDescuento, dSubtotal, iFactura, iNumFolioFactura, bEstatus,
                   dtFechaPago
            FROM TranCuentasClientes
            WHERE iCodPaciente = :codigo
            ORDER BY dtFecha DESC
            """,
            parametros,
        ),
        "citas": db.filas(
            """
            SELECT iCodCalendario, dtFecha, vchHora, vchTipoMotivo, vchServicio,
                   iCodEstado, vchNombreMedico
            FROM TranCalendario
            WHERE iCodPaciente = :codigo
            ORDER BY dtFecha DESC
            """,
            parametros,
        ),
        "documentos": _documentos_paciente(codigo),
    }


def _documentos_paciente(codigo: str) -> list[dict[str, Any]]:
    try:
        return db.filas(
            "SELECT id, categoria, titulo, nombre_original, mime, bytes, subido_en, notas "
            "FROM documentos WHERE iCodPaciente = :codigo ORDER BY subido_en DESC",
            {"codigo": codigo},
        )
    except Exception:  # noqa: BLE001 - la tabla puede no existir en una base vieja
        return []


def saldo_paciente(codigo: str) -> dict[str, Any]:
    datos = db.fila(
        """
        SELECT
          (SELECT COALESCE(SUM(dCuentaAdeudo), 0) FROM TranCorteCuentaCliente
            WHERE iCodPaciente = :codigo) AS pendiente,
          (SELECT COALESCE(SUM(dPrecioMenudeo), 0) FROM TranCuentasClientes
            WHERE iCodPaciente = :codigo) AS consumido
        """,
        {"codigo": codigo},
    ) or {}
    return {
        "pendiente": datos.get("pendiente") or 0,
        "consumido": datos.get("consumido") or 0,
    }


# --------------------------------------------------------------------------
# Informes médicos
# --------------------------------------------------------------------------

_FILTRO_INFORME = """
    (:q = '' OR i.vchMotivo LIKE :like OR i.sDiagnosticoPresuntivo LIKE :like
     OR i.sResultado LIKE :like OR a.vchNombrePaciente LIKE :like
     OR CONCAT_WS(' ', a.vchNombre, a.vchPaterno, a.vchMaterno) LIKE :like)
"""


def listar_informes(busqueda: str = "", pagina: int = 1) -> dict[str, Any]:
    busqueda = busqueda.strip()
    parametros = {"q": busqueda, "like": _patron(busqueda)}
    total = int(db.escalar(
        f"""
        SELECT COUNT(*) FROM TranInformeMedico i
        LEFT JOIN TranAfiliado a ON a.iCodPaciente = i.iCodPaciente
        WHERE {_FILTRO_INFORME}
        """,
        parametros,
    ) or 0)
    pagina = max(1, pagina)
    registros = db.filas(
        f"""
        SELECT i.iCodInformeMedico, i.vchNumInformeMedico, i.dtFechaInformeMedico,
               i.vchMotivo, i.sDiagnosticoPresuntivo, i.vchMedico, i.dPeso,
               i.dTemperatura, i.iCodPaciente, a.vchNombrePaciente,
               CONCAT_WS(' ', a.vchNombre, a.vchPaterno, a.vchMaterno) AS propietario
        FROM TranInformeMedico i
        LEFT JOIN TranAfiliado a ON a.iCodPaciente = i.iCodPaciente
        WHERE {_FILTRO_INFORME}
        ORDER BY i.dtFechaInformeMedico DESC, i.iCodInformeMedico DESC
        LIMIT :limite OFFSET :desplazamiento
        """,
        {**parametros, "limite": POR_PAGINA, "desplazamiento": (pagina - 1) * POR_PAGINA},
    )
    return {
        "registros": registros,
        "total": total,
        "pagina": pagina,
        "por_pagina": POR_PAGINA,
        "paginas": max(1, -(-total // POR_PAGINA)),
        "busqueda": busqueda,
    }


def obtener_informe(codigo: str) -> dict[str, Any] | None:
    return db.fila(
        """
        SELECT i.*, a.vchNombrePaciente, a.vchSexo, a.vchRaza, a.vchColor,
               a.dtFecNacimiento, a.iCodEspecie, a.vchNombre, a.vchPaterno,
               a.vchMaterno, a.vchTelefono, a.vchCorreo, a.vchDireccion,
               e.vchEspecie
        FROM TranInformeMedico i
        LEFT JOIN TranAfiliado a ON a.iCodPaciente = i.iCodPaciente
        LEFT JOIN CatEspecies e ON e.iCodEspecie = a.iCodEspecie
        WHERE i.iCodInformeMedico = :codigo
        """,
        {"codigo": codigo},
    )


# --------------------------------------------------------------------------
# Exámenes
# --------------------------------------------------------------------------

_FILTRO_EXAMEN = """
    (:q = '' OR x.vchDescripcion LIKE :like OR x.vchObservaciones LIKE :like
     OR x.vchNombreArchivo LIKE :like OR a.vchNombrePaciente LIKE :like)
"""


def listar_examenes(busqueda: str = "", pagina: int = 1) -> dict[str, Any]:
    busqueda = busqueda.strip()
    parametros = {"q": busqueda, "like": _patron(busqueda)}
    total = int(db.escalar(
        f"""
        SELECT COUNT(*) FROM TranExamenes x
        LEFT JOIN TranAfiliado a ON a.iCodPaciente = x.iCodPaciente
        WHERE {_FILTRO_EXAMEN}
        """,
        parametros,
    ) or 0)
    pagina = max(1, pagina)
    registros = db.filas(
        f"""
        SELECT x.iCodTranExamen, x.dtFecha, x.vchDescripcion, x.vchObservaciones,
               x.vchNombreArchivo, x.tiEstatus, x.iCodPaciente, a.vchNombrePaciente,
               CONCAT_WS(' ', a.vchNombre, a.vchPaterno, a.vchMaterno) AS propietario
        FROM TranExamenes x
        LEFT JOIN TranAfiliado a ON a.iCodPaciente = x.iCodPaciente
        WHERE {_FILTRO_EXAMEN}
        ORDER BY x.dtFecha DESC
        LIMIT :limite OFFSET :desplazamiento
        """,
        {**parametros, "limite": POR_PAGINA, "desplazamiento": (pagina - 1) * POR_PAGINA},
    )
    return {
        "registros": registros,
        "total": total,
        "pagina": pagina,
        "por_pagina": POR_PAGINA,
        "paginas": max(1, -(-total // POR_PAGINA)),
        "busqueda": busqueda,
    }


# --------------------------------------------------------------------------
# Panel y navegador de tablas
# --------------------------------------------------------------------------

def informes_recientes(limite: int = 8) -> list[dict[str, Any]]:
    return db.filas(
        """
        SELECT i.iCodInformeMedico, i.dtFechaInformeMedico, i.vchMotivo,
               i.sDiagnosticoPresuntivo, i.iCodPaciente, a.vchNombrePaciente
        FROM TranInformeMedico i
        LEFT JOIN TranAfiliado a ON a.iCodPaciente = i.iCodPaciente
        ORDER BY i.dtFechaInformeMedico DESC, i.iCodInformeMedico DESC
        LIMIT :limite
        """,
        {"limite": limite},
    )


def proximas_citas(limite: int = 8) -> list[dict[str, Any]]:
    return db.filas(
        """
        SELECT c.iCodCalendario, c.dtFecha, c.vchHora, c.vchTipoMotivo, c.vchServicio,
               c.iCodPaciente, a.vchNombrePaciente
        FROM TranCalendario c
        LEFT JOIN TranAfiliado a ON a.iCodPaciente = c.iCodPaciente
        WHERE c.dtFecha >= CURDATE()
        ORDER BY c.dtFecha, c.vchHora
        LIMIT :limite
        """,
        {"limite": limite},
    )


def tablas_con_conteo() -> list[dict[str, Any]]:
    resultado = []
    for tabla in TABLAS:
        filas = 0
        try:
            filas = int(db.escalar(f"SELECT COUNT(*) FROM `{tabla.nombre}`") or 0)
        except Exception:  # noqa: BLE001 - tabla aún no creada
            filas = 0
        resultado.append({
            "nombre": tabla.nombre,
            "etiqueta": tabla.etiqueta,
            "grupo": tabla.grupo,
            "filas": filas,
            "clave": ", ".join(tabla.clave),
        })
    return resultado


def filas_tabla(nombre: str, pagina: int = 1) -> dict[str, Any] | None:
    tabla = POR_NOMBRE.get(nombre)
    if not tabla:
        return None
    total = int(db.escalar(f"SELECT COUNT(*) FROM `{tabla.nombre}`") or 0)
    pagina = max(1, pagina)
    registros = db.filas(
        f"SELECT * FROM `{tabla.nombre}` LIMIT :limite OFFSET :desplazamiento",
        {"limite": POR_PAGINA, "desplazamiento": (pagina - 1) * POR_PAGINA},
    )
    columnas = list(registros[0].keys()) if registros else []
    return {
        "tabla": tabla,
        "registros": registros,
        "columnas": columnas,
        "total": total,
        "pagina": pagina,
        "paginas": max(1, -(-total // POR_PAGINA)),
    }
