"""Genera el libro Excel con los datos consolidados para el cliente.

Toma la base que usa el visor (con las correcciones aplicadas) y arma hojas
legibles: resumen, pacientes con su propietario y sus totales, informes,
vacunas, exámenes, cuenta, citas, correcciones, notas y conteo por tabla.

Uso:
    .\\.venv\\Scripts\\python.exe tools\\exportar_datos_cliente.py
    .\\.venv\\Scripts\\python.exe tools\\exportar_datos_cliente.py --salida dist\\datos.xlsx
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app import db  # noqa: E402
from app.campos import etiqueta as etiqueta_campo  # noqa: E402
from app.esquema import TABLAS  # noqa: E402

VERDE = "146F6A"
VERDE_CLARO = "E7F4F1"

# Panther puede tener dos fichas del mismo paciente (mismo código, otra fecha).
# Para las hojas de detalle se une contra una sola: la más reciente.
_JOIN_PACIENTE = """
    LEFT JOIN (
        SELECT a1.iCodPaciente, a1.vchNombrePaciente
        FROM TranAfiliado a1
        WHERE a1.dtFecha = (
            SELECT MAX(a2.dtFecha) FROM TranAfiliado a2
            WHERE a2.iCodPaciente = a1.iCodPaciente
        )
    ) a ON a.iCodPaciente = {columna}
"""


def _si_no(valor) -> str:
    return "Sí" if str(valor).strip().lower() in {"1", "true", "si", "sí"} else "No"


def _texto(valor) -> str:
    if valor is None:
        return ""
    texto = str(valor).strip()
    return "" if texto in {".", "-", "--"} else texto


def _consultar(sql: str) -> pd.DataFrame:
    return pd.DataFrame(db.filas(sql))


def pacientes() -> pd.DataFrame:
    marco = _consultar(
        """
        SELECT a.iCodPaciente, a.chCodPaciente, a.iNoPaciente,
               a.vchNombrePaciente, e.vchEspecie, a.vchRaza, a.vchSexo, a.vchColor,
               a.dtFecNacimiento, a.bActivo, a.bCastrado,
               a.vchNombre, a.vchPaterno, a.vchMaterno,
               a.vchTelefono, a.vchTelefono2, a.vchCorreo, a.vchCorreo2,
               a.vchDireccion, a.vchColonia, a.vchCiudad, a.vchRFC,
               a.vchObservaciones, a.vchNombreMedico,
               (SELECT MAX(i.dtFechaInformeMedico) FROM TranInformeMedico i
                 WHERE i.iCodPaciente = a.iCodPaciente) AS ultima_visita,
               (SELECT COUNT(*) FROM TranInformeMedico i
                 WHERE i.iCodPaciente = a.iCodPaciente) AS informes,
               (SELECT COUNT(*) FROM TranRegistroVacunas v
                 WHERE v.iCodPaciente = a.iCodPaciente) AS vacunas,
               (SELECT COUNT(*) FROM TranExamenes x
                 WHERE x.iCodPaciente = a.iCodPaciente) AS examenes,
               (SELECT COALESCE(SUM(c.dCuentaAdeudo), 0) FROM TranCorteCuentaCliente c
                 WHERE c.iCodPaciente = a.iCodPaciente) AS saldo_pendiente
        FROM pacientes_vista a
        LEFT JOIN CatEspecies e ON e.iCodEspecie = a.iCodEspecie
        ORDER BY a.vchNombrePaciente, a.chCodPaciente
        """
    )
    marco["bActivo"] = marco["bActivo"].apply(_si_no)
    marco["bCastrado"] = marco["bCastrado"].apply(_si_no)
    for columna in ("chCodPaciente", "vchRaza", "vchColor", "vchPaterno",
                    "vchMaterno", "vchTelefono2", "vchCorreo2", "vchColonia",
                    "vchRFC", "vchObservaciones", "vchNombreMedico"):
        marco[columna] = marco[columna].apply(_texto)
    marco = marco.rename(columns={
        "iCodPaciente": "Código de paciente",
        "chCodPaciente": "Código corto",
        "iNoPaciente": "Expediente",
        "vchNombrePaciente": "Paciente",
        "vchEspecie": "Especie",
        "vchRaza": "Raza",
        "vchSexo": "Sexo",
        "vchColor": "Color",
        "dtFecNacimiento": "Nacimiento",
        "bActivo": "Activo",
        "bCastrado": "Castrado",
        "vchNombre": "Propietario (nombre)",
        "vchPaterno": "Propietario (paterno)",
        "vchMaterno": "Propietario (materno)",
        "vchTelefono": "Teléfono",
        "vchTelefono2": "Teléfono 2",
        "vchCorreo": "Correo",
        "vchCorreo2": "Correo 2",
        "vchDireccion": "Dirección",
        "vchColonia": "Sector",
        "vchCiudad": "Ciudad",
        "vchRFC": "Identificación",
        "vchObservaciones": "Observaciones",
        "vchNombreMedico": "Médico asignado",
        "ultima_visita": "Última visita",
        "informes": "Informes",
        "vacunas": "Vacunas",
        "examenes": "Exámenes",
        "saldo_pendiente": "Saldo pendiente",
    })
    return marco


def informes() -> pd.DataFrame:
    marco = _consultar(
        f"""
        SELECT i.iCodPaciente, a.vchNombrePaciente, i.vchNumInformeMedico,
               i.dtFechaInformeMedico, i.vchMotivo, i.vchNota,
               i.sDiagnosticoPresuntivo, i.sDiagnosticoDiferencial,
               i.sPruebasRequeridas, i.sResultado, i.vchReceta,
               i.vchMedico, i.dPeso, i.dTemperatura
        FROM TranInformeMedico i
        {_JOIN_PACIENTE.format(columna='i.iCodPaciente')}
        ORDER BY i.dtFechaInformeMedico DESC, i.iCodInformeMedico DESC
        """
    )
    return marco.rename(columns={
        "iCodPaciente": "Código de paciente",
        "vchNombrePaciente": "Paciente",
        "vchNumInformeMedico": "N.º informe",
        "dtFechaInformeMedico": "Fecha",
        "vchMotivo": "Motivo",
        "vchNota": "Nota clínica",
        "sDiagnosticoPresuntivo": "Diagnóstico presuntivo",
        "sDiagnosticoDiferencial": "Diagnóstico diferencial",
        "sPruebasRequeridas": "Pruebas requeridas",
        "sResultado": "Resultado",
        "vchReceta": "Receta",
        "vchMedico": "Médico",
        "dPeso": "Peso",
        "dTemperatura": "Temperatura",
    })


def vacunas() -> pd.DataFrame:
    marco = _consultar(
        f"""
        SELECT v.iCodPaciente, a.vchNombrePaciente, v.dtFecha, v.sVacunaAplicada,
               v.sNumeroLote, v.sProximaVacuna, v.dtFechaProgramada, v.dPeso
        FROM TranRegistroVacunas v
        {_JOIN_PACIENTE.format(columna='v.iCodPaciente')}
        ORDER BY v.dtFecha DESC
        """
    )
    return marco.rename(columns={
        "iCodPaciente": "Código de paciente",
        "vchNombrePaciente": "Paciente",
        "dtFecha": "Fecha",
        "sVacunaAplicada": "Vacuna",
        "sNumeroLote": "Lote",
        "sProximaVacuna": "Próxima vacuna",
        "dtFechaProgramada": "Próxima fecha",
        "dPeso": "Peso",
    })


def examenes() -> pd.DataFrame:
    marco = _consultar(
        f"""
        SELECT x.iCodPaciente, a.vchNombrePaciente, x.dtFecha, x.vchDescripcion,
               x.vchObservaciones, x.vchNombreArchivo
        FROM TranExamenes x
        {_JOIN_PACIENTE.format(columna='x.iCodPaciente')}
        ORDER BY x.dtFecha DESC
        """
    )
    return marco.rename(columns={
        "iCodPaciente": "Código de paciente",
        "vchNombrePaciente": "Paciente",
        "dtFecha": "Fecha",
        "vchDescripcion": "Examen",
        "vchObservaciones": "Observaciones",
        "vchNombreArchivo": "Archivo",
    })


def cuenta() -> pd.DataFrame:
    marco = _consultar(
        f"""
        SELECT c.iCodPaciente, a.vchNombrePaciente, c.dtFecha, c.vchServicio,
               c.dCantidad, c.dPrecioMenudeo, c.dSubtotal, c.iNumFolioFactura,
               c.dtFechaPago
        FROM TranCuentasClientes c
        {_JOIN_PACIENTE.format(columna='c.iCodPaciente')}
        ORDER BY c.dtFecha DESC
        """
    )
    return marco.rename(columns={
        "iCodPaciente": "Código de paciente",
        "vchNombrePaciente": "Paciente",
        "dtFecha": "Fecha",
        "vchServicio": "Servicio",
        "dCantidad": "Cantidad",
        "dPrecioMenudeo": "Precio",
        "dSubtotal": "Subtotal",
        "iNumFolioFactura": "Factura",
        "dtFechaPago": "Fecha de pago",
    })


def citas() -> pd.DataFrame:
    marco = _consultar(
        f"""
        SELECT c.iCodPaciente, a.vchNombrePaciente, c.dtFecha, c.vchHora,
               c.vchTipoMotivo, c.vchServicio, c.vchNombreMedico
        FROM TranCalendario c
        {_JOIN_PACIENTE.format(columna='c.iCodPaciente')}
        ORDER BY c.dtFecha DESC
        """
    )
    return marco.rename(columns={
        "iCodPaciente": "Código de paciente",
        "vchNombrePaciente": "Paciente",
        "dtFecha": "Fecha",
        "vchHora": "Hora",
        "vchTipoMotivo": "Motivo",
        "vchServicio": "Servicio",
        "vchNombreMedico": "Médico",
    })


def correcciones() -> pd.DataFrame:
    marco = _consultar(
        """
        SELECT campo, valor, valor_original, usuario, motivo, actualizada_en
        FROM correcciones WHERE tabla = 'TranAfiliado'
        ORDER BY actualizada_en DESC
        """
    )
    if not marco.empty:
        marco["campo"] = marco["campo"].apply(etiqueta_campo)
    if marco.empty:
        return pd.DataFrame(columns=["Campo", "Valor corregido", "Valor original",
                                     "Usuario", "Motivo", "Fecha"])
    return marco.rename(columns={
        "campo": "Campo",
        "valor": "Valor corregido",
        "valor_original": "Valor original",
        "usuario": "Usuario",
        "motivo": "Motivo",
        "actualizada_en": "Fecha",
    })


def notas() -> pd.DataFrame:
    marco = _consultar(
        """
        SELECT iCodPaciente, nota, usuario, creada_en
        FROM notas_paciente ORDER BY creada_en DESC
        """
    )
    if marco.empty:
        return pd.DataFrame(columns=["Código de paciente", "Nota", "Usuario", "Fecha"])
    return marco.rename(columns={
        "iCodPaciente": "Código de paciente",
        "nota": "Nota",
        "usuario": "Usuario",
        "creada_en": "Fecha",
    })


def conteos() -> pd.DataFrame:
    filas = []
    for tabla in TABLAS:
        try:
            total = int(db.escalar(f"SELECT COUNT(*) FROM `{tabla.nombre}`") or 0)
        except Exception:  # noqa: BLE001 - tabla ausente
            total = 0
        filas.append({"Tabla": tabla.etiqueta, "Nombre técnico": tabla.nombre, "Filas": total})
    return pd.DataFrame(filas)


def resumen(pacientes_df: pd.DataFrame, informes_df: pd.DataFrame) -> pd.DataFrame:
    try:
        ultima = db.fila("SELECT iniciada_en, estado, filas FROM importaciones ORDER BY id DESC LIMIT 1")
    except Exception:  # noqa: BLE001
        ultima = None

    datos = [
        ("Generado", datetime.now().strftime("%d/%m/%Y %H:%M")),
        ("Base de datos", f"{db.motor().url.database}"),
        ("Pacientes (fichas)", len(pacientes_df)),
        ("Pacientes con código único", int(db.escalar(
            "SELECT COUNT(DISTINCT iCodPaciente) FROM TranAfiliado") or 0)),
        ("Fichas repetidas del mismo código", int(db.escalar(
            "SELECT COUNT(*) - COUNT(DISTINCT iCodPaciente) FROM TranAfiliado") or 0)),
        ("Informes médicos", len(informes_df)),
        ("Exámenes", int(db.escalar("SELECT COUNT(*) FROM TranExamenes") or 0)),
        ("Vacunas aplicadas", int(db.escalar("SELECT COUNT(*) FROM TranRegistroVacunas") or 0)),
        ("Citas", int(db.escalar("SELECT COUNT(*) FROM TranCalendario") or 0)),
        ("Movimientos de cuenta", int(db.escalar("SELECT COUNT(*) FROM TranCuentasClientes") or 0)),
        ("Correcciones del visor", int(db.escalar("SELECT COUNT(*) FROM correcciones") or 0)),
        ("Notas internas", int(db.escalar("SELECT COUNT(*) FROM notas_paciente") or 0)),
        ("Última importación", ultima["iniciada_en"].strftime("%d/%m/%Y %H:%M") if ultima else "—"),
        ("Filas de la última importación", ultima["filas"] if ultima else "—"),
    ]
    return pd.DataFrame(datos, columns=["Dato", "Valor"])


def _formatear(hoja, formato_fecha: bool = True) -> None:
    hoja.freeze_panes = "A2"
    hoja.auto_filter.ref = hoja.dimensions
    hoja.row_dimensions[1].height = 22
    for celda in hoja[1]:
        celda.font = Font(bold=True, color="FFFFFF", size=10)
        celda.fill = PatternFill("solid", fgColor=VERDE)
        celda.alignment = Alignment(vertical="center")

    for columna in hoja.columns:
        letra = get_column_letter(columna[0].column)
        largo = max((len(str(celda.value)) for celda in columna if celda.value is not None), default=10)
        hoja.column_dimensions[letra].width = min(max(largo + 2, 12), 55)
        if formato_fecha:
            for celda in columna[1:]:
                if isinstance(celda.value, (datetime, date)):
                    celda.number_format = "DD/MM/YYYY"


def exportar(salida: Path) -> Path:
    salida.parent.mkdir(parents=True, exist_ok=True)
    pacientes_df = pacientes()
    informes_df = informes()

    hojas = [
        ("Resumen", resumen(pacientes_df, informes_df)),
        ("Pacientes", pacientes_df),
        ("Informes", informes_df),
        ("Vacunas", vacunas()),
        ("Exámenes", examenes()),
        ("Cuenta", cuenta()),
        ("Citas", citas()),
        ("Correcciones", correcciones()),
        ("Notas internas", notas()),
        ("Tablas", conteos()),
    ]

    with pd.ExcelWriter(salida, engine="openpyxl") as escritor:
        for nombre, marco in hojas:
            marco.to_excel(escritor, sheet_name=nombre, index=False)
            _formatear(escritor.sheets[nombre])

        # El resumen se lee mejor con la primera columna más ancha.
        resumen_hoja = escritor.sheets["Resumen"]
        resumen_hoja.column_dimensions["A"].width = 32
        resumen_hoja.column_dimensions["B"].width = 30
        for celda in resumen_hoja["A"]:
            celda.font = Font(bold=True, color="152B33")
            celda.fill = PatternFill("solid", fgColor=VERDE_CLARO)

        tablas_hoja = escritor.sheets["Tablas"]
        for celda in tablas_hoja["C"][1:]:
            celda.number_format = "#,##0"

    return salida


def main() -> int:
    analizador = argparse.ArgumentParser(description="Exportar los datos a un libro Excel")
    analizador.add_argument(
        "--salida",
        default=str(RAIZ / "dist" / f"VetVisor-datos-{date.today().isoformat()}.xlsx"),
    )
    argumentos = analizador.parse_args()
    ruta = exportar(Path(argumentos.salida))
    print(f"Libro generado: {ruta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
