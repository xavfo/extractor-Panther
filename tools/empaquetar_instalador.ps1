param(
    [string]$Version = "",
    [string]$CarpetaSalida = "dist"
)

$ErrorActionPreference = "Stop"
$raiz = Split-Path $PSScriptRoot -Parent
Set-Location $raiz

if (-not $Version) {
    if (-not (Test-Path "VERSION")) {
        Write-Error "Falta el archivo VERSION."
        exit 1
    }
    $Version = (Get-Content "VERSION" -Raw).Trim()
}

$respaldo = Join-Path $raiz "sql\vetvisor_completo.sql"
if (-not (Test-Path $respaldo)) {
    Write-Error "Falta el respaldo sql\vetvisor_completo.sql. Ejecuta primero tools\exportar_base.ps1"
    exit 1
}

$destino = Join-Path $raiz $CarpetaSalida
$staging = Join-Path $destino "VetVisor-$Version"
if (Test-Path $staging) { Remove-Item -Recurse -Force $staging }
New-Item -ItemType Directory -Force -Path $staging | Out-Null

$elementos = @(
    "app", "tools", "instalador", "sql", "docs",
    "requirements.txt", "README.md", ".env.example", "VERSION"
)
foreach ($elemento in $elementos) {
    $origen = Join-Path $raiz $elemento
    if (-not (Test-Path $origen)) {
        Write-Error "Falta '$elemento' en el repositorio."
        exit 1
    }
    Copy-Item -Path $origen -Destination $staging -Recurse -Force
}

# Limpiar cachés de Python y el empaquetador (no se necesita en el servidor)
Get-ChildItem $staging -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force
Get-ChildItem $staging -Recurse -File -Include "*.pyc", "*.pyo" -ErrorAction SilentlyContinue |
    Remove-Item -Force
$empaquetador = Join-Path $staging "tools\empaquetar_instalador.ps1"
if (Test-Path $empaquetador) { Remove-Item $empaquetador -Force }

$zip = Join-Path $destino "VetVisor-instalador-$Version.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $zip -CompressionLevel Optimal

$hash = (Get-FileHash $zip -Algorithm SHA256).Hash
$archivoHash = "$zip.sha256"
Set-Content -Path $archivoHash -Value "$hash  VetVisor-instalador-$Version.zip" -Encoding ASCII

$tamano = [math]::Round((Get-Item $zip).Length / 1MB, 2)
Write-Host "Paquete: $zip ($tamano MB)"
Write-Host "SHA256:  $hash"
Write-Host ""
Write-Host "Contenido del paquete:"
Get-ChildItem $staging | Select-Object Name | Format-Table -HideTableHeaders
