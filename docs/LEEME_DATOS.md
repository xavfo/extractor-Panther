# Datos consolidados de VetVisor

Este paquete contiene **los datos que hoy tiene el visor**, listos para revisar
o restaurar. Corresponde a la primera versión entregada al local.

## Contenido

| Archivo | Qué es |
| --- | --- |
| `VetVisor-base-AAAA-MM-DD.sql` | Respaldo completo de MySQL: estructura y datos de las 36 tablas de Panther, más `correcciones`, `notas_paciente`, `auditoria`, `documentos` e `importaciones` |
| `VetVisor-datos-AAAA-MM-DD.xlsx` | Libro legible con resumen, pacientes, informes, vacunas, exámenes, cuenta, citas, correcciones, notas y conteo por tabla |
| `LEEME.md` | Este documento |

## Qué hay dentro

- **710 fichas de pacientes** (700 códigos de paciente únicos: en Panther hay 10
  mascotas con dos fichas registradas en fechas distintas; se conservan las dos
  para no perder historia).
- **1 145 informes médicos**, **86 exámenes**, **350 vacunas**, **476 citas** y
  **1 693 movimientos de cuenta**, entre otros.
- Los datos del libro Excel muestran las **correcciones hechas en el visor**
  (por ejemplo, un teléfono actualizado). El respaldo SQL conserva además el
  valor original en la tabla `correcciones`, para poder restaurarlo.
- **No se incluye la tabla `usuarios`**: son credenciales del visor y no forman
  parte de los datos del cliente. Al instalar, el administrador se crea aparte.

## Cómo restaurar el respaldo

Opción recomendada, usando las herramientas del proyecto:

```powershell
.\.venv\Scripts\python.exe tools\instalar_base.py --name vetvisor_copia --sql RUTA\VetVisor-base-AAAA-MM-DD.sql
```

Opción con el cliente de MySQL:

```powershell
mysql -h 127.0.0.1 -P 3307 -u root -e "CREATE DATABASE vetvisor_copia CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -h 127.0.0.1 -P 3307 -u root vetvisor_copia -e "source RUTA\VetVisor-base-AAAA-MM-DD.sql"
```

Después hay que crear el administrador con `tools\crear_admin.py` o arrancar el
visor, que lo crea si la tabla `usuarios` está vacía.

## Cómo comprobar que llegó completo

```sql
SELECT COUNT(*) FROM TranAfiliado;      -- 710
SELECT COUNT(*) FROM TranInformeMedico; -- 1145
SELECT COUNT(*) FROM TranExamenes;      -- 86
SELECT COUNT(*) FROM TranRegistroVacunas; -- 350
```

En el libro Excel, la hoja **Resumen** repite estos conteos y la fecha de
generación.

## Privacidad

El paquete contiene nombres, teléfonos, correos y datos clínicos de clientes
reales. Debe viajar solo por canales del local y no publicarse ni compartirse
fuera de la veterinaria.
