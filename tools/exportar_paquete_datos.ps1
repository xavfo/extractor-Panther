param(
    [string]$Salida = "dist"
)

$ErrorActionPreference = "Stop"
$raiz = Split-Path $PSScriptRoot -Parent
Set-Location $raiz

$fecha = Get-Date -Format "yyyy-MM-dd"
$carpeta = Join-Path $raiz (Join-Path $Salida "VetVisor-datos-$fecha")
if (Test-Path $carpeta) { Remove-Item -Recurse -Force $carpeta }
New-Item -ItemType Directory -Force -Path $carpeta | Out-Null

Write-Host "== Generando respaldo SQL con datos"
.\tools\exportar_base.ps1
Copy-Item "sql\vetvisor_completo.sql" (Join-Path $carpeta "VetVisor-base-$fecha.sql") -Force

Write-Host "== Generando libro Excel consolidado"
& ".venv\Scripts\python.exe" "tools\exportar_datos_cliente.py" `
    --salida (Join-Path $carpeta "VetVisor-datos-$fecha.xlsx")
if ($LASTEXITCODE -ne 0) {
    Write-Error "Falló la generación del libro Excel."
    exit 1
}

Copy-Item "docs\LEEME_DATOS.md" (Join-Path $carpeta "LEEME.md") -Force

Write-Host "== Comprobando conteos"
$env:PYTHONIOENCODING = "utf-8"
& ".venv\Scripts\python.exe" -c @'
from app import db
for tabla, etiqueta in (('TranAfiliado', 'pacientes'), ('TranInformeMedico', 'informes'),
                        ('TranExamenes', 'exámenes'), ('TranRegistroVacunas', 'vacunas')):
    total = db.escalar(f"SELECT COUNT(*) FROM `{tabla}`")
    print(f"   {etiqueta}: {total}")
'@

$zip = Join-Path $raiz (Join-Path $Salida "VetVisor-datos-$fecha.zip")
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path (Join-Path $carpeta "*") -DestinationPath $zip -CompressionLevel Optimal

$hash = (Get-FileHash $zip -Algorithm SHA256).Hash
Set-Content -Path "$zip.sha256" -Value "$hash  VetVisor-datos-$fecha.zip" -Encoding ASCII
$tamano = [math]::Round((Get-Item $zip).Length / 1MB, 2)

Write-Host ""
Write-Host "Paquete: $zip ($tamano MB)"
Write-Host "SHA256:  $hash"
Write-Host ""
Get-ChildItem $carpeta | Select-Object Name, @{n='MB'; e={[math]::Round($_.Length/1MB,2)}} | Format-Table -AutoSize
