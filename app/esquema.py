"""Esquema: qué tablas de Panther se importan y cómo se tipan sus columnas.

Panther exporta 38 tablas. Se importan tal cual (mismo nombre de tabla y de
columna que el XLSX) para que cualquier persona que conozca Panther encuentre lo
mismo en MySQL. El tipado se deduce del nombre de la columna, con una lista
explícita de columnas largas; así, si Panther agrega una columna, el importador
la crea sola sin tocar código.

Nunca se importan contraseñas ni PIN del sistema de origen: no hacen falta para
consultar y no deben quedar en otra base.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .db import ejecutar


@dataclass(frozen=True)
class Tabla:
    nombre: str
    archivo: str
    clave: tuple[str, ...]
    etiqueta: str
    grupo: str
    orden: int = 100
    reemplazar: bool = False
    columnas_visibles: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Cambios:
    """Qué tuvo que ajustarse al comparar el XLSX con la tabla existente."""

    agregadas: tuple[str, ...] = ()
    recreada: bool = False


# Orden y agrupación usados en el navegador de tablas.
TABLAS: tuple[Tabla, ...] = (
    Tabla("TranAfiliado", "TranAfiliado.xlsx", ("iCodPaciente", "dtFecha"),
          "Pacientes y propietarios", "Clínica", 1),
    Tabla("TranInformeMedico", "TranInformeMedico.xlsx", ("iCodInformeMedico",),
          "Informes médicos", "Clínica", 2),
    Tabla("TranInformeMedicoHistorico", "TranInformeMedicoHistorico.xlsx",
          ("iCodPaciente", "iCodInformeMedico"), "Informes médicos (histórico)", "Clínica", 3),
    Tabla("TranExamenes", "TranExamenes.xlsx", ("iCodTranExamen",),
          "Exámenes", "Clínica", 4),
    Tabla("TranRegistroVacunas", "TranRegistroVacunas.xlsx", ("iCodVacuna",),
          "Vacunas aplicadas", "Clínica", 5),
    Tabla("TranDesparacitacion", "TranDesparacitacion.xlsx", ("iCodDesparacitacion",),
          "Desparasitaciones", "Clínica", 6),
    Tabla("TranCirugias", "TranCirugias.xlsx", ("iCodCirugia",),
          "Cirugías", "Clínica", 7),
    Tabla("TranHospitalizacion", "TranHospitalizacion.xlsx", ("iCodTranHospitalizacion",),
          "Hospitalización", "Clínica", 8),
    Tabla("TranCalendario", "TranCalendario.xlsx", ("_huella",),
          "Citas del calendario", "Agenda", 20, reemplazar=True),
    Tabla("disAgenda", "disAgenda.xlsx", ("iCodMatriz",),
          "Agenda diaria", "Agenda", 21),
    Tabla("TranCentroNotificaciones", "TranCentroNotificaciones.xlsx", ("iCodNotificacion",),
          "Notificaciones", "Agenda", 22),
    Tabla("TranCuentasClientes", "TranCuentasClientes.xlsx", ("iCodCuentaCliente",),
          "Movimientos de cuenta", "Finanzas", 40),
    Tabla("TranCorteCuentaCliente", "TranCorteCuentaCliente.xlsx", ("iCodCorteCuentaCliente",),
          "Cortes de cuenta", "Finanzas", 41),
    Tabla("TranAbonosCuentasClientes", "TranAbonosCuentasClientes.xlsx", ("iCodAbono",),
          "Abonos de clientes", "Finanzas", 42),
    Tabla("TranCorteCaja", "TranCorteCaja.xlsx", ("iCodCorteDia",),
          "Cortes de caja", "Finanzas", 43),
    Tabla("RelProductos", "RelProductos.xlsx", ("iCodProductoLote",),
          "Lotes de productos", "Inventario", 50),
    Tabla("CatProductos", "CatProductos.xlsx", ("iCodProducto",),
          "Productos", "Catálogos", 60),
    Tabla("CatServicios", "CatServicios.xlsx", ("iCodServicio",),
          "Servicios", "Catálogos", 61),
    Tabla("CatTipoServicios", "CatTipoServicios.xlsx", ("iCodCatTipoServicio",),
          "Tipos de servicio", "Catálogos", 62),
    Tabla("CatEspecies", "CatEspecies.xlsx", ("iCodEspecie",),
          "Especies", "Catálogos", 63),
    Tabla("CatRazas", "CatRazas.xlsx", ("iCodRaza",),
          "Razas", "Catálogos", 64),
    Tabla("CatEspeciesRazas", "CatEspeciesRazas.xlsx", ("iCodEspecie", "iCodRaza"),
          "Razas por especie", "Catálogos", 65),
    Tabla("CatColor", "CatColor.xlsx", ("iCodColor",),
          "Colores", "Catálogos", 66),
    Tabla("CatMarcas", "CatMarcas.xlsx", ("iCodMarca",),
          "Marcas", "Catálogos", 67),
    Tabla("CatLaboratorios", "CatLaboratorios.xlsx", ("iCodLaboratorio",),
          "Laboratorios", "Catálogos", 68),
    Tabla("CatProveedores", "CatProveedores.xlsx", ("iCodProveedor",),
          "Proveedores", "Catálogos", 69),
    Tabla("CatProveedorInternet", "CatProveedorInternet.xlsx", ("iCodProveedorInternet",),
          "Proveedores en línea", "Catálogos", 70),
    Tabla("CatMedico", "CatMedico.xlsx", ("iCodMedico",),
          "Personal médico", "Catálogos", 71),
    Tabla("CatEmpresas", "CatEmpresas.xlsx", ("iCodEmpresa",),
          "Datos de la empresa", "Catálogos", 72),
    Tabla("CatMotivos", "CatMotivos.xlsx", ("iCodMotivo",),
          "Motivos de consulta", "Catálogos", 73),
    Tabla("CatCorreosTextos", "CatCorreosTextos.xlsx", ("iCodCorreoTextos",),
          "Plantillas de correo", "Catálogos", 74),
    Tabla("CatReportesTextos", "CatReportesTextos.xlsx", ("iCodCatReporte",),
          "Textos de reportes", "Catálogos", 75),
    Tabla("CatSGC_Peso20Y", "CatSGC_Peso20Y.xlsx", ("Id", "Sex", "Agemos"),
          "Curva de peso (0 a 20 años)", "Crecimiento", 80),
    Tabla("CatSGC_Altura20Y", "CatSGC_Altura20Y.xlsx", ("Id", "Sex", "Agemos"),
          "Curva de talla (0 a 20 años)", "Crecimiento", 81),
    Tabla("CatSGC_Peso36M", "CatSGC_Peso36M.xlsx", ("Id", "Sex", "Agemos"),
          "Curva de peso (0 a 36 meses)", "Crecimiento", 82),
    Tabla("CatSGC_Altura36M", "CatSGC_Altura36M.xlsx", ("Id", "Sex", "Agemos"),
          "Curva de talla (0 a 36 meses)", "Crecimiento", 83),
)

POR_NOMBRE: dict[str, Tabla] = {tabla.nombre: tabla for tabla in TABLAS}

# No se importan: son credenciales del sistema de origen.
COLUMNAS_OMITIDAS = {
    "vchPassword",
    "vchPasswordResp",
    "vchPasswordCloud",
    "vchPin",
    "vchUsuario",
}

# Columnas que pueden traer párrafos completos (TEXT evita el límite de fila).
COLUMNAS_TEXTO = {
    "vchObservaciones", "vchDescripcion", "vchMotivo", "vchNota", "vchProblema",
    "vchReceta", "vchDiagnostico", "vchMotivoIngreso", "vchMotivoCancelacion",
    "vchNotificacion", "vchDetalleNotificacion", "vchCorreccion", "vchServicio",
    "vchTipoMotivo", "vchTipoServicio", "vchTipoNotificacion",
    "vchTextoSpanish", "vchTextoIngles", "vchTituloSpanish", "vchTituloIngles",
    "vchAsuntoL1", "vchDescripcionL1", "vchPieL1",
    "vchAsuntoL2", "vchDescripcionL2", "vchPieL2",
    "vchDireccion", "vchDireccionFiscal", "vchNombreFiscal",
    "sDiagnosticoPresuntivo", "sDiagnosticoDiferencial", "sPruebasRequeridas",
    "sResultado", "sObservaciones", "vchProveedor",
}

# Índices que sostienen las pantallas (búsqueda de pacientes y su historia).
INDICES: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "TranAfiliado": (
        ("idx_pac_nombre", ("vchNombrePaciente",)),
        ("idx_pac_propietario", ("vchPaterno", "vchMaterno", "vchNombre")),
        ("idx_pac_telefono", ("vchTelefono",)),
        ("idx_pac_correo", ("vchCorreo",)),
    ),
    "TranInformeMedico": (
        ("idx_inf_paciente_fecha", ("iCodPaciente", "dtFechaInformeMedico")),
    ),
    "TranExamenes": (("idx_exa_paciente_fecha", ("iCodPaciente", "dtFecha")),),
    "TranRegistroVacunas": (("idx_vac_paciente_fecha", ("iCodPaciente", "dtFecha")),),
    "TranDesparacitacion": (("idx_des_paciente_fecha", ("iCodPaciente", "dtFecha")),),
    "TranCirugias": (("idx_cir_paciente_fecha", ("iCodPaciente", "dtFecha")),),
    "TranHospitalizacion": (("idx_hos_paciente", ("iCodPaciente",)),),
    "TranCuentasClientes": (("idx_cta_paciente_fecha", ("iCodPaciente", "dtFecha")),),
    "TranCalendario": (
        ("idx_cal_fecha", ("dtFecha",)),
        ("idx_cal_paciente", ("iCodPaciente",)),
    ),
    "disAgenda": (("idx_agenda_fecha", ("dtFecha",)),),
}


def tipo_columna(columna: str) -> str:
    """Tipo MySQL deducido del nombre de la columna de Panther."""
    if columna == "_huella":
        return "CHAR(40)"
    if columna in COLUMNAS_TEXTO or columna.startswith("vchTextoOpcional"):
        return "LONGTEXT"
    if columna == "Imagen" or columna.startswith("img"):
        return "LONGTEXT"
    if columna.startswith("iCod") or columna == "iNoPaciente":
        return "VARCHAR(64)"
    if columna.startswith("dt"):
        return "DATETIME"
    if columna == "Id":
        return "INT"
    if columna == "Sex":
        return "TINYINT"
    if columna == "Agemos":
        return "DECIMAL(8,2)"
    if columna.startswith("Diff"):
        return "DECIMAL(18,6)"
    if columna.startswith("d") and columna[1:2].isupper():
        return "DECIMAL(18,6)"
    if columna.startswith("b") and columna[1:2].isupper():
        return "TINYINT(1)"
    if columna.startswith("ti") and columna[2:3].isupper():
        return "TINYINT"
    if columna.startswith("si") and columna[2:3].isupper():
        return "INT"
    if columna.startswith("i") and columna[1:2].isupper():
        return "INT"
    if columna in {"L", "M", "S"} or (columna.startswith("P") and columna[1:].isdigit()):
        return "DECIMAL(18,6)"
    if columna.startswith("Pub") and columna[3:].isdigit():
        return "DECIMAL(18,6)"
    return "VARCHAR(255)"


def tabla_existe(nombre: str) -> bool:
    from .db import escalar

    return bool(escalar(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema = DATABASE() AND table_name = :nombre",
        {"nombre": nombre},
    ))


def columnas_existentes(nombre: str) -> list[str]:
    from .db import filas

    return [
        fila["nombre"]
        for fila in filas(
            "SELECT column_name AS nombre FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = :nombre "
            "ORDER BY ordinal_position",
            {"nombre": nombre},
        )
    ]


def _clave_actual(nombre: str) -> list[str]:
    from .db import filas

    return [
        fila["columna"]
        for fila in filas(
            "SELECT column_name AS columna FROM information_schema.statistics "
            "WHERE table_schema = DATABASE() AND table_name = :nombre "
            "AND index_name = 'PRIMARY' ORDER BY seq_in_index",
            {"nombre": nombre},
        )
    ]


def asegurar_tabla(tabla: Tabla, columnas: list[str]) -> Cambios:
    """Crea o ajusta la tabla. Devuelve los cambios aplicados.

    Si la clave primaria de la tabla existente no coincide con la declarada, la
    tabla se reconstruye: es un espejo del export, así que la fuente manda.
    """
    columnas = [columna for columna in columnas if columna not in COLUMNAS_OMITIDAS]
    destino = list(columnas)
    if "_huella" in tabla.clave and "_huella" not in destino:
        destino.insert(0, "_huella")

    faltantes_clave = [clave for clave in tabla.clave if clave not in destino]
    if faltantes_clave:
        raise ValueError(
            f"{tabla.archivo}: no se encontró la columna clave {faltantes_clave}"
        )

    recreada = False
    if tabla_existe(tabla.nombre):
        clave_actual = _clave_actual(tabla.nombre)
        if clave_actual != list(tabla.clave):
            ejecutar(f"DROP TABLE `{tabla.nombre}`")
            recreada = True

    if recreada or not tabla_existe(tabla.nombre):
        definiciones = [
            f"`{columna}` {tipo_columna(columna)} "
            f"{'NOT NULL' if columna == '_huella' else 'NULL'}"
            for columna in destino
        ]
        claves = ", ".join(f"`{clave}`" for clave in tabla.clave)
        ejecutar(
            f"CREATE TABLE `{tabla.nombre}` ("
            + ", ".join(definiciones)
            + f", PRIMARY KEY ({claves})"
            + ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
        )
        agregadas: list[str] = []
    else:
        existentes = set(columnas_existentes(tabla.nombre))
        agregadas = [columna for columna in destino if columna not in existentes]
        for columna in agregadas:
            ejecutar(
                f"ALTER TABLE `{tabla.nombre}` "
                f"ADD COLUMN `{columna}` {tipo_columna(columna)} NULL"
            )

    _asegurar_indices(tabla)
    return Cambios(agregadas=tuple(agregadas), recreada=recreada)


def _asegurar_indices(tabla: Tabla) -> None:
    from .db import escalar

    for nombre, columnas in INDICES.get(tabla.nombre, ()):
        existe = escalar(
            "SELECT COUNT(*) FROM information_schema.statistics "
            "WHERE table_schema = DATABASE() AND table_name = :tabla "
            "AND index_name = :indice",
            {"tabla": tabla.nombre, "indice": nombre},
        )
        if existe:
            continue
        lista = ", ".join(f"`{columna}`" for columna in columnas)
        ejecutar(
            f"ALTER TABLE `{tabla.nombre}` ADD INDEX `{nombre}` ({lista})"
        )


TABLAS_PROPIAS = """
CREATE TABLE IF NOT EXISTS `usuarios` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `usuario` VARCHAR(64) NOT NULL UNIQUE,
  `nombre` VARCHAR(160) NOT NULL,
  `correo` VARCHAR(160) NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `rol` VARCHAR(20) NOT NULL DEFAULT 'recepcion',
  `activo` TINYINT(1) NOT NULL DEFAULT 1,
  `creado_en` DATETIME NOT NULL,
  `ultimo_acceso` DATETIME NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `auditoria` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `usuario_id` INT NULL,
  `usuario` VARCHAR(64) NULL,
  `tabla` VARCHAR(64) NOT NULL,
  `clave` VARCHAR(128) NOT NULL,
  `accion` VARCHAR(20) NOT NULL,
  `campo` VARCHAR(64) NULL,
  `valor_anterior` LONGTEXT NULL,
  `valor_nuevo` LONGTEXT NULL,
  `fecha` DATETIME NOT NULL,
  `ip` VARCHAR(64) NULL,
  INDEX `idx_auditoria_clave` (`tabla`, `clave`),
  INDEX `idx_auditoria_fecha` (`fecha`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `documentos` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `iCodPaciente` VARCHAR(64) NULL,
  `categoria` VARCHAR(32) NOT NULL,
  `titulo` VARCHAR(200) NOT NULL,
  `nombre_original` VARCHAR(255) NOT NULL,
  `ruta` VARCHAR(500) NOT NULL,
  `mime` VARCHAR(120) NULL,
  `bytes` BIGINT NULL,
  `subido_por` INT NULL,
  `subido_en` DATETIME NOT NULL,
  `notas` TEXT NULL,
  INDEX `idx_documentos_paciente` (`iCodPaciente`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `importaciones` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `iniciada_en` DATETIME NOT NULL,
  `terminada_en` DATETIME NULL,
  `origen` VARCHAR(500) NULL,
  `estado` VARCHAR(20) NOT NULL,
  `tablas` INT NOT NULL DEFAULT 0,
  `filas` INT NOT NULL DEFAULT 0,
  `archivos` INT NOT NULL DEFAULT 0,
  `detalle` LONGTEXT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `importacion_tablas` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `importacion_id` INT NOT NULL,
  `tabla` VARCHAR(64) NOT NULL,
  `filas` INT NULL,
  `columnas` INT NULL,
  `error` TEXT NULL,
  INDEX `idx_importacion` (`importacion_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


def asegurar_tablas_propias() -> None:
    for sentencia in TABLAS_PROPIAS.split(";"):
        if sentencia.strip():
            ejecutar(sentencia)
