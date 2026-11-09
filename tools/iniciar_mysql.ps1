param(
    [int]$Puerto = 3307
)

$mysqld = "C:\xampp\mysql\bin\mysqld.exe"
$myIni = "C:\xampp\mysql\bin\my.ini"

if (-not (Test-Path $mysqld)) {
    Write-Error "No se encontró MySQL de XAMPP en $mysqld"
    exit 1
}

$escucha = Get-NetTCPConnection -LocalPort $Puerto -State Listen -ErrorAction SilentlyContinue
if ($escucha) {
    Write-Host "El puerto $Puerto ya está en uso: MySQL parece estar corriendo."
    exit 0
}

Start-Process -FilePath $mysqld `
    -ArgumentList "--defaults-file=$myIni", "--port=$Puerto" `
    -WindowStyle Minimized

Write-Host "MySQL iniciado en el puerto $Puerto (ventana minimizada)."
