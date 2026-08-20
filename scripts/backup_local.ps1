# Respaldo de la base de datos (SQLite) y los archivos generados (media/)
# para la instalacion local sin Docker.
# Uso manual:   powershell -ExecutionPolicy Bypass -File scripts\backup_local.ps1
# Uso programado: ver instrucciones al final de este archivo.

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackupsDir  = Join-Path $ProjectRoot "backups"
$Timestamp   = Get-Date -Format "yyyy-MM-dd_HHmmss"
$DestZip     = Join-Path $BackupsDir "backup_$Timestamp.zip"

New-Item -ItemType Directory -Force -Path $BackupsDir | Out-Null

$Staging = Join-Path $env:TEMP "microfinanzas_backup_$Timestamp"
New-Item -ItemType Directory -Force -Path $Staging | Out-Null

Copy-Item -Path (Join-Path $ProjectRoot "db.sqlite3") -Destination $Staging -ErrorAction SilentlyContinue
Copy-Item -Path (Join-Path $ProjectRoot "media") -Destination $Staging -Recurse -ErrorAction SilentlyContinue

Compress-Archive -Path "$Staging\*" -DestinationPath $DestZip -Force
Remove-Item -Path $Staging -Recurse -Force

Write-Host "Backup creado: $DestZip"

# Retencion: conserva solo los ultimos 8 backups (2 anios si es trimestral).
Get-ChildItem -Path $BackupsDir -Filter "backup_*.zip" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -Skip 8 |
    Remove-Item -Force

# --- Para programarlo cada 3 meses en el Programador de tareas de Windows ---
# Ejecutar UNA VEZ en PowerShell (ajustando la ruta del proyecto):
#
#   schtasks /create /tn "MicroFinanzasBackup" /sc MONTHLY /mo 3 /st 02:00 /tr "powershell.exe -ExecutionPolicy Bypass -File C:\ruta\al\proyecto\scripts\backup_local.ps1"
#
# Para verificarlo:  schtasks /query /tn "MicroFinanzasBackup"
# Para eliminarlo:   schtasks /delete /tn "MicroFinanzasBackup" /f
