$WshShell = New-Object -comObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "Comic Scanlation Studio.lnk"
$TargetPath = Join-Path $PSScriptRoot "run.bat"
$IconPath = Join-Path $PSScriptRoot "assets\icon.ico"

$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetPath
$Shortcut.WorkingDirectory = $PSScriptRoot
$Shortcut.WindowStyle = 1 # Normal window
$Shortcut.Description = "Launch Comic Scanlation Studio (Source)"

# Verify icon exists, otherwise use default
if (Test-Path $IconPath) {
    $Shortcut.IconLocation = "$IconPath, 0"
}

$Shortcut.Save()

Write-Host "Shortcut created on Desktop: $ShortcutPath"
Write-Host "You can now launch the app directly from your desktop!"
