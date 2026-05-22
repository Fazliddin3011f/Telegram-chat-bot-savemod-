param(
    [Parameter(Mandatory=$true)]
    [string]$BackupZip
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$TempDir = Join-Path $env:TEMP ("tg-ton-ai-bot_restore_" + (Get-Date -Format "yyyy-MM-dd_HH-mm-ss"))

if (!(Test-Path $BackupZip)) {
    throw "Backup topilmadi: $BackupZip"
}

New-Item -ItemType Directory -Force -Path $TempDir | Out-Null
Expand-Archive -Path $BackupZip -DestinationPath $TempDir -Force
Copy-Item -Path (Join-Path $TempDir "*") -Destination $Root -Recurse -Force
Remove-Item -Recurse -Force $TempDir

Write-Host "Backup tiklandi: $BackupZip"
