param(
    [string]$DbHost = "127.0.0.1",
    [int]$DbPort = 3307,
    [string]$DbUser = "root",
    [string]$DbPassword = "",
    [string]$DbName = "vetvisor",
    [string]$Salida = "sql\vetvisor_completo.sql"
)

$ErrorActionPreference = "Stop"
$raiz = Split-Path $PSScriptRoot -Parent
Set-Location $raiz

$mysqldump = "C:\xampp\mysql\bin\mysqldump.exe"
if (-not (Test-Path $mysqldump)) {
    $orden = Get-Command mysqldump -ErrorAction SilentlyContinue
    if ($orden) { $mysqldump = $orden.Source }
}
if (-not (Test-Path $mysqldump)) {
    Write-Error "No se encontró mysqldump. Indícalo en el PATH o instala MySQL."
    exit 1
}

$destino = Join-Path $raiz $Salida
New-Item -ItemType Directory -Force -Path (Split-Path $destino -Parent) | Out-Null

$anterior = $env:MYSQL_PWD
$env:MYSQL_PWD = $DbPassword
try {
    & $mysqldump `
        -h $DbHost -P $DbPort -u $DbUser `
        --default-character-set=utf8mb4 `
        --single-transaction --quick --skip-lock-tables --add-drop-table `
        --ignore-table="$DbName.usuarios" `
        --result-file="$destino" $DbName
    if ($LASTEXITCODE -ne 0) {
        Write-Error "mysqldump falló con código $LASTEXITCODE"
        exit 1
    }
} finally {
    $env:MYSQL_PWD = $anterior
}

$tamano = [math]::Round((Get-Item $destino).Length / 1MB, 2)
Write-Host "Respaldo generado: $destino ($tamano MB)"
Write-Host "Incluye estructura y datos, excepto la tabla 'usuarios' (se crea al instalar)."
