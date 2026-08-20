# Arranca la app localmente (sin Docker) usando el entorno virtual del
# proyecto y Waitress como servidor WSGI (gunicorn no corre en Windows).
#
# Uso manual:      powershell -ExecutionPolicy Bypass -File scripts\start_local.ps1
# Uso programado:  ver instrucciones en el mensaje de configuracion (Tarea
#                   Programada, disparador "Al iniciar sesion").
#
# Si el proceso de Waitress se cae, este script lo vuelve a levantar
# automaticamente (equivalente a "restart: unless-stopped" de Docker).

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe   = Join-Path $ProjectRoot "env\Scripts\python.exe"
$LogsDir     = Join-Path $ProjectRoot "logs"

if (-not (Test-Path $PythonExe)) {
    Write-Error "No se encontro el entorno virtual en '$ProjectRoot\env'. Sigue el paso de configuracion inicial primero (crear venv + pip install)."
    exit 1
}

New-Item -ItemType Directory -Force -Path $LogsDir | Out-Null
Set-Location $ProjectRoot

$LogFile = Join-Path $LogsDir ("server_{0}.log" -f (Get-Date -Format "yyyy-MM-dd"))

function Log($msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

Log "Aplicando migraciones..."
& $PythonExe manage.py migrate --no-input 2>&1 | Tee-Object -FilePath $LogFile -Append

Log "Verificando usuario administrador inicial..."
& $PythonExe manage.py crear_admin_inicial 2>&1 | Tee-Object -FilePath $LogFile -Append

Log "Recolectando archivos estaticos..."
& $PythonExe manage.py collectstatic --no-input 2>&1 | Tee-Object -FilePath $LogFile -Append

Log "Iniciando servidor Waitress en el puerto 8000..."

while ($true) {
    & $PythonExe -m waitress --listen=0.0.0.0:8000 miwebsite.wsgi:application 2>&1 | Tee-Object -FilePath $LogFile -Append
    Log "El servidor se detuvo (codigo $LASTEXITCODE). Reiniciando en 5 segundos... (Ctrl+C para cancelar)"
    Start-Sleep -Seconds 5
}
