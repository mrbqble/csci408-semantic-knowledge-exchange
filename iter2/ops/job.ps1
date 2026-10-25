param([string]$Name, [string]$Cmd)
# Runs a long job as an on-demand Windows scheduled task (no trigger), so it survives the Desktop Commander shell.
$dir = "C:\Users\mrbqble\Desktop\csci408-probe\iter2"
New-Item -ItemType Directory -Force "$dir\jobs" | Out-Null
$cmdFile = "$dir\jobs\$Name.cmd"
$body = "@echo off`r`ncd /d $dir`r`nset PYTHONUNBUFFERED=1`r`necho START %date% %time% > jobs\$Name.log`r`n$Cmd`r`necho EXIT %errorlevel% %date% %time% >> jobs\$Name.log`r`n"
Set-Content -Path $cmdFile -Value $body -Encoding ascii
$action = New-ScheduledTaskAction -Execute $cmdFile
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 72)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive
Unregister-ScheduledTask -TaskName "csci408_$Name" -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName "csci408_$Name" -Action $action -Settings $settings -Principal $principal | Out-Null
Start-ScheduledTask -TaskName "csci408_$Name"
Write-Output "started csci408_$Name"
