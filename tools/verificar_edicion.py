"""Verifica la capa de edición sin dejar datos.

Abre una transacción, inserta una corrección de prueba sobre un paciente real y
comprueba que la vista `pacientes_vista` la devuelve y que la clave única impide
duplicarla. Al final hace ROLLBACK: la base queda igual que antes.

Uso:
    .\\.venv\\Scripts\\python.exe tools\\verificar_edicion.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pymysql

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app.config import AJUSTES  # noqa: E402

VALOR_PRUEBA = "VERIFICACION-000"


def main() -> int:
    conexion = pymysql.connect(
        host=AJUSTES.db_host,
        port=AJUSTES.db_puerto,
        user=AJUSTES.db_usuario,
        password=AJUSTES.db_password,
        database=AJUSTES.db_nombre,
        charset="utf8mb4",
        autocommit=False,
    )
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.views "
                "WHERE table_schema = DATABASE() AND table_name = 'pacientes_vista'"
            )
            if not cursor.fetchone()[0]:
                print("FALLO: no existe la vista pacientes_vista.")
                return 1

            cursor.execute(
                """
                SELECT a.iCodPaciente, a.vchTelefono
                FROM TranAfiliado a
                WHERE NOT EXISTS (
                    SELECT 1 FROM correcciones c
                    WHERE c.tabla = 'TranAfiliado'
                      AND c.clave = a.iCodPaciente
                      AND c.campo = 'vchTelefono'
                )
                ORDER BY a.vchNombrePaciente
                LIMIT 1
                """
            )
            paciente = cursor.fetchone()
            if not paciente:
                print("FALLO: no hay pacientes disponibles para la prueba.")
                return 1

            codigo, original = paciente
            cursor.execute(
                "INSERT INTO correcciones "
                "(tabla, clave, campo, valor, valor_original, usuario_id, usuario, "
                "motivo, creada_en, actualizada_en) "
                "VALUES ('TranAfiliado', %s, 'vchTelefono', %s, %s, 0, 'verificador', "
                "'prueba automática', NOW(), NOW())",
                (codigo, VALOR_PRUEBA, "" if original is None else original),
            )

            cursor.execute(
                "SELECT vchTelefono FROM pacientes_vista "
                "WHERE iCodPaciente = %s ORDER BY dtFecha DESC LIMIT 1",
                (codigo,),
            )
            mostrado = cursor.fetchone()
            if not mostrado or mostrado[0] != VALOR_PRUEBA:
                print(f"FALLO: la vista no mostró la corrección (devolvió {mostrado}).")
                conexion.rollback()
                return 1

            try:
                cursor.execute(
                    "INSERT INTO correcciones "
                    "(tabla, clave, campo, valor, usuario_id, usuario, creada_en, actualizada_en) "
                    "VALUES ('TranAfiliado', %s, 'vchTelefono', 'otro', 0, 'verificador', NOW(), NOW())",
                    (codigo,),
                )
                print("FALLO: se permitió duplicar una corrección del mismo campo.")
                conexion.rollback()
                return 1
            except pymysql.err.IntegrityError:
                pass

            conexion.rollback()
            print(
                "OK: la vista muestra la corrección, la clave única evita duplicados "
                "y la transacción se revirtió sin dejar datos."
            )
            return 0
    finally:
        conexion.close()


if __name__ == "__main__":
    raise SystemExit(main())
