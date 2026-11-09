param(
    [int]$Puerto = 8000
)

Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Error "Falta el entorno virtual. Crea .venv e instala requirements.txt."
    exit 1
}

Write-Host "VetVisor en http://0.0.0.0:$Puerto (Ctrl+C para detener)."
& ".venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port $Puerto
