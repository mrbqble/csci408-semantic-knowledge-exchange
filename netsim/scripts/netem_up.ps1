<#
 netem_up.ps1 - idempotent bring-up of the network-emulation prerequisites (Windows host).
   1. loads sch_netem / sch_tbf / sch_htb into the shared WSL2 kernel (must be redone after every
      `wsl --shutdown` or reboot; WSL ships the module files, it does not load them)
   2. makes sure the Docker engine is up
   3. -Smoke : runs a netem qdisc inside a throw-away container as an end-to-end check
 Never unregister a WSL distro while the VM is running: that left the kernel's RCU-tasks stalled
 (module loads then hang until `wsl --shutdown`). The script reports that state if it finds it.
#>
param([switch]$Smoke, [string]$Distro = 'Ubuntu')

function Fail($m) { Write-Host "FAIL: $m" -ForegroundColor Red; exit 1 }

$stall = (wsl -d $Distro -u root -- bash -c "dmesg | grep -c tasks_rcu_exit_srcu_stall" 2>$null | Select-Object -Last 1)
if ([int]$stall -gt 0) { Fail "kernel RCU-tasks stall present ($stall log lines): module loads will hang. Run 'wsl --shutdown', then re-run this script." }

wsl -d $Distro -u root -- timeout 30 modprobe -a sch_netem sch_tbf sch_htb 2>$null
if ($LASTEXITCODE -eq 124) { Fail "modprobe timed out (kernel stalled). Run 'wsl --shutdown' and retry." }
if ($LASTEXITCODE -ne 0)   { Fail "modprobe exit code $LASTEXITCODE" }
$mods = wsl -d $Distro -u root -- bash -c "grep -oE '^sch_(netem|tbf|htb)' /proc/modules | sort | tr '\n' ' '" 2>$null
Write-Host "kernel modules loaded: $mods"

$exe = 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
docker info --format '{{.ServerVersion}}' *> $null
if ($LASTEXITCODE -ne 0) {
    if (-not (Get-Process 'Docker Desktop' -ErrorAction SilentlyContinue)) { Start-Process $exe }
    for ($i = 0; $i -lt 24; $i++) { Start-Sleep 5; docker info --format '{{.ServerVersion}}' *> $null; if ($LASTEXITCODE -eq 0) { break } }
    if ($LASTEXITCODE -ne 0) { Fail 'Docker engine did not come up within 2 minutes' }
}
Write-Host ("docker engine: " + (docker info --format '{{.ServerVersion}}'))

if ($Smoke) {
    $out = docker run --rm --cap-add NET_ADMIN alpine sh -c 'apk add --no-cache iproute2-tc >/dev/null 2>&1 && timeout 10 tc qdisc add dev eth0 root netem delay 40ms rate 1mbit; echo exit=$?; tc qdisc show dev eth0' 2>&1
    $out | ForEach-Object { Write-Host "  $_" }
    if (-not ($out -match 'exit=0')) { Fail 'netem smoke test failed inside the container' }
}
Write-Host 'OK: netem ready' -ForegroundColor Green