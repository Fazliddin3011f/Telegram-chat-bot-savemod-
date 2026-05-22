$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackupDir = Join-Path $Root "backups"
$Stamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$ZipPath = Join-Path $BackupDir "tg-ton-ai-bot_$Stamp.zip"
$TempDir = Join-Path $env:TEMP "tg-ton-ai-bot_backup_$Stamp"

New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
New-Item -ItemType Directory -Force -Path $TempDir | Out-Null

$Items = @(
    "bot.py",
    "fragmently.py",
    "requirements.txt",
    "README.md",
    ".env",
    "bot_settings.json",
    "savemod\main.py",
    "savemod\db.py",
    "savemod\requirements.txt",
    "savemod\README.md",
    "savemod\.env",
    "savemod\savemod.session",
    "savemod\cache.db",
    "savemod\media"
)

foreach ($Item in $Items) {
    $Source = Join-Path $Root $Item
    if (Test-Path $Source) {
        $Destination = Join-Path $TempDir $Item
        $DestinationParent = Split-Path -Parent $Destination
        New-Item -ItemType Directory -Force -Path $DestinationParent | Out-Null
        Copy-Item -Path $Source -Destination $Destination -Recurse -Force
    }
}

Compress-Archive -Path (Join-Path $TempDir "*") -DestinationPath $ZipPath -Force
Remove-Item -Recurse -Force $TempDir

Write-Host "Backup tayyor: $ZipPath"
