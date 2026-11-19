# Registers a daily Windows Task Scheduler job (09:00) for the Research Digest Bot.
# Run in PowerShell:  powershell -ExecutionPolicy Bypass -File scripts\install_windows.ps1
$BotDir = Split-Path -Parent $PSScriptRoot
$Py = (Get-Command python).Source
$Action = New-ScheduledTaskAction -Execute $Py -Argument "`"$BotDir\digest.py`"" -WorkingDirectory $BotDir
$Trigger = New-ScheduledTaskTrigger -Daily -At 9am
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable   # catches up missed runs
Register-ScheduledTask -TaskName "ResearchDigestBot" -Action $Action -Trigger $Trigger -Settings $Settings -Force
Write-Host "Installed task 'ResearchDigestBot' (daily 09:00, runs late if the PC was off)."
