#Requires -Version 5.1
<#
.SYNOPSIS
    Instala VetVisor (aplicación + base con datos) en este equipo.

.DESCRIPTION
    Crea el entorno de Python, prepara MySQL, carga el respaldo con los datos
    actuales, escribe la configuración, crea el usuario administrador y deja el
    visor listo para abrirse desde la red del local.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File instalador\instalar.ps1

.EXAMPLE
    .\instalador\instalar.ps1 -DbPort 3306 -DbUser root -DbPassword "clave" -Puerto 8080
#>
[CmdletBinding()]
param(
    [string]$DbHost = "127.0.0.1",
    [int]$DbPort = 3307,
    [string]$DbUser = "root",
    [string]$DbPassword = "",
    [string]$DbName = "vetvisor",
    [int]$Puerto = 8000,
    [string]$AdminUsuario = "admin",
    [string]$AdminPassword = "",
    [string]$Python = "",
    [switch]$Restaurar,
    [switch]$AbrirFirewall,
    [switch]$SinIniciar
)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

# El instalador manda: si la sesión hereda variables del entorno de otro
# proyecto, se ignoran para que valga exactamente lo que se escribe en .env.
foreach ($variableApp in @(
    "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD",
    "SECRETO_SESION", "ADMIN_USUARIO", "ADMIN_PASSWORD",
    "RUTA_EXPORTACION", "RUTA_ALMACEN", "QUFACT_URL", "QUFACT_TOKEN"
)) {
    Remove-Item "Env:$variableApp" -ErrorAction SilentlyContinue
}

function Paso([string]$texto) {
    Write-Host ""
    Write-Host "== $texto" -ForegroundColor Cyan
}
function Info([string]$texto) { Write-Host "   $texto" }
function Aviso([string]$texto) { Write-Host "AVISO: $texto" -ForegroundColor Yellow }
function Fallar([string]$texto) {
    Write-Host ""
    Write-Host "ERROR: $texto" -ForegroundColor Red
    exit 1
}

function Puerto-Abierto([string]$nombre, [int]$puerto) {
    $cliente = New-Object System.Net.Sockets.TcpClient
    try {
        $tarea = $cliente.ConnectAsync($nombre, $puerto)
        if (-not $tarea.Wait(1500)) { return $false }
        return $cliente.Connected
    } catch {
        return $false
    } finally {
        $cliente.Dispose()
    }
}

function Env-Cita([string]$valor) {
    if ($null -eq $valor) { $valor = "" }
    $escapado = $valor.Replace('\', '\\').Replace('"', '\"')
    return '"' + $escapado + '"'
}

Write-Host "VetVisor · instalador" -ForegroundColor Green
Write-Host "Carpeta: $raiz"

# ---------------------------------------------------------------- Python
Paso "Comprobando Python"
$lanzador = $null
if ($Python) {
    if (-not (Test-Path $Python)) {
        Fallar "No existe el intérprete indicado en -Python: $Python"
    }
    $lanzador = $Python
} else {
    foreach ($candidato in @("py", "python")) {
        $orden = Get-Command $candidato -ErrorAction SilentlyContinue
        if ($orden) { $lanzador = $orden.Source; break }
    }
}
if (-not $lanzador) {
    Fallar "No se encontró Python 3. Instálalo desde python.org y marca 'Add python.exe to PATH', o indica la ruta con -Python."
}
$version = & $lanzador -c "import sys; print('%d.%d' % sys.version_info[:2])"
$partes = $version.Split(".")
if ([int]$partes[0] -ne 3 -or [int]$partes[1] -lt 10) {
    Fallar "Se necesita Python 3.10 o superior (se encontró $version en $lanzador)."
}
Info "Python $version ($lanzador)"

$venvPy = Join-Path $raiz ".venv\Scripts\python.exe"
if (Test-Path $venvPy) {
    $versionVenv = & $venvPy -c "import sys; print('%d.%d' % sys.version_info[:2])"
    if ($versionVenv -ne $version) {
        Fallar "La carpeta .venv usa Python $versionVenv y el instalador encontró $version. Elimina .venv y vuelve a ejecutar (o indica -Python con la versión del entorno)."
    }
}
if (-not (Test-Path $venvPy)) {
    Paso "Creando entorno virtual"
    & $lanzador -m venv .venv
    if (-not (Test-Path $venvPy)) { Fallar "No se pudo crear la carpeta .venv." }
}

Paso "Instalando dependencias"
& $venvPy -m pip install --disable-pip-version-check --quiet --upgrade pip
& $venvPy -m pip install --disable-pip-version-check --quiet -r requirements.txt
if ($LASTEXITCODE -ne 0) { Fallar "Falló la instalación de dependencias." }

# ---------------------------------------------------------------- MySQL
Paso "Comprobando MySQL en $DbHost`:$DbPort"
if (-not (Puerto-Abierto $DbHost $DbPort)) {
    $iniciar = Join-Path $raiz "tools\iniciar_mysql.ps1"
    if (Test-Path $iniciar) {
        Info "MySQL no responde; intentando iniciar el de XAMPP…"
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $iniciar -Puerto $DbPort | Out-Null
        for ($intento = 0; $intento -lt 30; $intento++) {
            if (Puerto-Abierto $DbHost $DbPort) { break }
            Start-Sleep -Milliseconds 700
        }
    }
}
if (-not (Puerto-Abierto $DbHost $DbPort)) {
    Fallar "MySQL no responde en $DbHost`:$DbPort. Enciéndelo o usa -DbHost, -DbPort, -DbUser y -DbPassword."
}
Info "MySQL responde"

# ---------------------------------------------------------------- Base
Paso "Preparando la base '$DbName'"
$respaldo = Join-Path $raiz "sql\vetvisor_completo.sql"
if (-not (Test-Path $respaldo)) {
    Fallar "Falta el respaldo 'sql\vetvisor_completo.sql'. Genera uno con tools\exportar_base.ps1."
}
$env:VETVISOR_DB_PASSWORD = $DbPassword
$parametrosBase = @(
    "tools\instalar_base.py",
    "--host", $DbHost,
    "--port", "$DbPort",
    "--user", $DbUser,
    "--name", $DbName,
    "--sql", $respaldo
)
if ($Restaurar) { $parametrosBase += "--restaurar" }
& $venvPy @parametrosBase
if ($LASTEXITCODE -ne 0) { Fallar "No se pudo cargar el respaldo en la base." }

# ---------------------------------------------------------------- .env
Paso "Escribiendo configuración"
$rutaEnv = Join-Path $raiz ".env"
$config = @{}
if (Test-Path $rutaEnv) {
    foreach ($linea in Get-Content -LiteralPath $rutaEnv) {
        if ($linea -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$') {
            $valor = $Matches[2].Trim()
            if ($valor.Length -ge 2 -and $valor.StartsWith('"') -and $valor.EndsWith('"')) {
                $valor = $valor.Substring(1, $valor.Length - 2)
                $valor = $valor.Replace('\"', '"').Replace('\\', '\')
            }
            $config[$Matches[1]] = $valor
        }
    }
}

$secreto = $config["SECRETO_SESION"]
if ([string]::IsNullOrWhiteSpace($secreto) -or $secreto -eq "cambia-esta-clave-por-una-larga-y-aleatoria") {
    $secreto = (& $venvPy -c "import secrets; print(secrets.token_urlsafe(48))").Trim()
}

if (-not $AdminPassword) {
    $seguro = Read-Host "Contraseña para el usuario '$AdminUsuario' (mínimo 8 caracteres)" -AsSecureString
    $puntero = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($seguro)
    try {
        $AdminPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($puntero)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($puntero)
    }
}
if ($AdminPassword.Length -lt 8) {
    Fallar "La contraseña del administrador debe tener al menos 8 caracteres."
}

$lineas = @(
    "# Configuración generada por el instalador de VetVisor",
    "DB_HOST=$DbHost",
    "DB_PORT=$DbPort",
    "DB_NAME=$DbName",
    "DB_USER=$DbUser",
    "DB_PASSWORD=$(Env-Cita $DbPassword)",
    "SECRETO_SESION=$secreto",
    "ADMIN_USUARIO=$AdminUsuario",
    "ADMIN_PASSWORD=$(Env-Cita $AdminPassword)",
    "RUTA_EXPORTACION=.src",
    "RUTA_ALMACEN=storage/documentos",
    "QUFACT_URL=http://127.0.0.1:8099",
    "QUFACT_TOKEN="
)
$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($rutaEnv, ($lineas -join "`r`n") + "`r`n", $utf8)
Info "Archivo .env creado"

# ---------------------------------------------------------------- Administrador
Paso "Creando el usuario administrador"
$resultadoAdmin = & $venvPy -c "from app import auth, esquema; esquema.asegurar_tablas_propias(); print('NUEVO' if auth.crear_admin_si_falta() else 'EXISTE')"
if ($LASTEXITCODE -ne 0) { Fallar "No se pudo preparar la tabla de usuarios." }
if ($resultadoAdmin -match "EXISTE") {
    Aviso "Ya existía un administrador: la contraseña no se cambió. Usa tools\crear_admin.py si necesitas restablecerla."
} else {
    Info "Administrador '$AdminUsuario' creado"
}

# La contraseña ya cumplió su función: no se deja escrita en el archivo.
$contenidoEnv = [System.IO.File]::ReadAllText($rutaEnv)
$contenidoEnv = [regex]::Replace($contenidoEnv, '(?m)^ADMIN_PASSWORD=[^\r\n]*', 'ADMIN_PASSWORD=')
[System.IO.File]::WriteAllText($rutaEnv, $contenidoEnv, $utf8)
Info "La contraseña no queda guardada en .env; anótala en un lugar seguro"

# ---------------------------------------------------------------- Lanzador
$bat = "@echo off`r`ncd /d `"%~dp0`"`r`npowershell -NoProfile -ExecutionPolicy Bypass -File `"tools\arrancar_visor.ps1`" -Puerto $Puerto`r`n"
[System.IO.File]::WriteAllText(
    (Join-Path $raiz "Iniciar VetVisor.bat"),
    $bat,
    (New-Object System.Text.UTF8Encoding($false))
)
Info "Creado 'Iniciar VetVisor.bat'"

# ---------------------------------------------------------------- Firewall
if ($AbrirFirewall) {
    Paso "Abriendo el puerto $Puerto en el firewall"
    try {
        $regla = "VetVisor $Puerto"
        if (-not (Get-NetFirewallRule -DisplayName $regla -ErrorAction SilentlyContinue)) {
            New-NetFirewallRule -DisplayName $regla -Direction Inbound `
                -LocalPort $Puerto -Protocol TCP -Action Allow | Out-Null
            Info "Regla creada"
        } else {
            Info "La regla ya existía"
        }
    } catch {
        Aviso "No se pudo crear la regla (requiere consola de administrador): $($_.Exception.Message)"
    }
}

# ---------------------------------------------------------------- Arranque
if (-not $SinIniciar) {
    if (Puerto-Abierto "127.0.0.1" $Puerto) {
        Info "El puerto $Puerto ya está atendiendo: no se inicia otro proceso."
    } else {
        Paso "Iniciando VetVisor"
        Start-Process -FilePath $venvPy `
            -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "$Puerto") `
            -WorkingDirectory $raiz -WindowStyle Minimized | Out-Null
    }

    $listo = $false
    for ($intento = 0; $intento -lt 25; $intento++) {
        Start-Sleep -Milliseconds 700
        try {
            $salud = Invoke-RestMethod -Uri "http://127.0.0.1:$Puerto/salud" -TimeoutSec 2
            if ($salud.base_datos -eq $true) { $listo = $true; break }
        } catch { }
    }
    if (-not $listo) {
        Aviso "El servidor no respondió la comprobación. Revisa la ventana minimizada o arranca con 'Iniciar VetVisor.bat'."
    }
}

# ---------------------------------------------------------------- Resumen
$ip = $null
try {
    $ip = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" } |
        Select-Object -First 1).IPAddress
} catch { }

Paso "Instalación terminada"
Info "Aplicación:     $raiz"
Info "Base de datos:  $DbName en $DbHost`:$DbPort"
Info "Usuario:        $AdminUsuario"
Info "Este equipo:    http://127.0.0.1:$Puerto"
if ($ip) { Info "Red del local:  http://$ip`:$Puerto" }
Info ""
Info "Para arrancar de nuevo: doble clic en 'Iniciar VetVisor.bat'."
if (-not $SinIniciar -and $ip) {
    Info "Si otro equipo no abre la página, permite el puerto con -AbrirFirewall."
}
