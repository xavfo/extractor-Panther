# Carpeta de respaldos SQL

Aquí se genera `vetvisor_completo.sql`, el respaldo que usa el instalador para
dejar la base con los datos actuales.

```powershell
.\tools\exportar_base.ps1
```

El archivo **no se versiona** porque contiene datos de pacientes y propietarios.
Incluye estructura y datos de las 36 tablas de Panther y de las tablas propias
(`auditoria`, `documentos`, `importaciones`, `importacion_tablas`), pero deja
fuera `usuarios` para que el instalador cree el administrador con la contraseña
que elija el operador.

Para restaurarlo en otra base sin pasar por el instalador:

```powershell
.\.venv\Scripts\python.exe tools\instalar_base.py --name vetvisor_copia --sql sql\vetvisor_completo.sql
```
