param(
    [int]$Puerto = 3307,
    [string]$Usuario = "root",
    [string]$Clave = ""
)

$mysqladmin = "C:\xampp\mysql\bin\mysqladmin.exe"

if (-not (Test-Path $mysqladmin)) {
    Write-Error "No se encontró mysqladmin en $mysqladmin"
    exit 1
}

$argumentos = @("-h", "127.0.0.1", "-P", "$Puerto", "-u", $Usuario)
if ($Clave) { $argumentos += "--password=$Clave" }
$argumentos += "shutdown"

& $mysqladmin @argumentos
Write-Host "MySQL detenido (puerto $Puerto)."
