# Instalación de VetVisor

Este paquete incluye **la aplicación y la base con los datos actuales**
(710 pacientes, 1 145 informes, 86 exámenes, 350 vacunas y el resto de tablas).
No viene con `.env`, `.venv` ni datos sueltos: todo se crea al instalar.

## Requisitos del equipo

- Windows 10 u 11.
- **Python 3.10 o superior** instalado y en el PATH.
- **MySQL o MariaDB** encendido. En el local se usa el de XAMPP; el instalador
  intenta arrancarlo solo si está en `C:\xampp`.
- Permiso para ejecutar scripts de PowerShell en esta sesión.

## Instalación en cuatro pasos

1. Descomprime el ZIP en una carpeta definitiva, por ejemplo `C:\VetVisor`.
   No lo dejes dentro de Descargas: esa carpeta se limpia.
2. Abre PowerShell en esa carpeta.
3. Ejecuta el instalador:

```powershell
powershell -ExecutionPolicy Bypass -File instalador\instalar.ps1
```

4. Cuando pregunte, escribe la contraseña del usuario administrador (mínimo 8
   caracteres). Al terminar te muestra la dirección para abrir el visor desde
   este equipo y desde la red del local.

> La contraseña que escribas **no queda guardada** en `.env`: solo se usa para
> crear la cuenta. Anótala en un lugar seguro; si la pierdes, se restablece con
> `tools\crear_admin.py`.

Si MySQL usa otro puerto, usuario o clave:

```powershell
powershell -ExecutionPolicy Bypass -File instalador\instalar.ps1 `
  -DbPort 3306 -DbUser root -DbPassword "tu-clave"
```

## Qué hace el instalador

1. Comprueba Python y crea `.venv` con las dependencias.
2. Verifica MySQL; si no responde y existe XAMPP, lo arranca.
3. Crea la base `vetvisor` y carga `sql\vetvisor_completo.sql`.
4. Escribe `.env` con una clave de sesión nueva y genera el usuario administrador.
5. Crea `Iniciar VetVisor.bat` y, si se lo pides, abre el puerto en el firewall.

Opciones útiles:

| Opción | Para qué |
| --- | --- |
| `-Puerto 8080` | cambiar el puerto del visor (por defecto 8000) |
| `-DbName otra_base` | instalar en otra base |
| `-Restaurar` | recargar el respaldo aunque la base ya tenga datos (sobrescribe) |
| `-AbrirFirewall` | permitir el puerto para los demás equipos de la LAN |
| `-SinIniciar` | no arrancar el visor al terminar |

## Arranque diario

Doble clic en **`Iniciar VetVisor.bat`**. La ventana minimizada es el servidor:
no la cierres mientras el local esté trabajando.

Para arrancarlo a mano, sin el `.bat`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Comprobación

- `http://127.0.0.1:8000/salud` debe responder
  `{"aplicacion":"vetvisor","base_datos":true}`.
- Al entrar, el panel debe mostrar los conteos de pacientes e informes.
- En *Base de datos*, la última importación debe figurar como **Ok**.

## Cosas que conviene saber

- **La tabla de usuarios no viaja en el respaldo.** El instalador la crea y da
  de alta al administrador con la contraseña que escribas.
- **Los datos del respaldo son de clientes reales.** No compartas el ZIP ni el
  archivo `sql\vetvisor_completo.sql` fuera del local.
- **Si reinstalas sobre una base existente**, el instalador no recarga nada por
  defecto (protege los datos). Para forzarlo, usa `-Restaurar`.
- **Desinstalar**: cierra la ventana del servidor, borra la carpeta del programa
  y, si corresponde, la base `vetvisor` desde MySQL. El respaldo queda en
  `sql\vetvisor_completo.sql` por si necesitas volver atrás.

## Problemas frecuentes

| Síntoma | Solución |
| --- | --- |
| «No se encontró Python 3» | Instala Python y marca *Add python.exe to PATH*; vuelve a abrir PowerShell |
| «MySQL no responde» | Enciende MySQL (XAMPP) o pasa `-DbPort`/`-DbUser`/`-DbPassword` |
| «No se pudo cargar el respaldo» | Revisa que MySQL esté encendido y que el usuario tenga permiso de crear bases |
| Otro equipo no abre la página | Ejecuta el instalador con `-AbrirFirewall` y confirma la IP que muestra |
