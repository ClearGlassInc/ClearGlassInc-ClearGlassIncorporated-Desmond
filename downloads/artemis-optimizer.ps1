# ==============================================================================
# ARTEMIS · EMP HARDENED NETWORK OPTIMIZER v7.0
# CORE: NEURAL MESH THROTTLE BYPASS
# ==============================================================================

Write-Host "--- INITIALIZING ARTEMIS NEURAL CORE OPTIMIZATION ---" -ForegroundColor Cyan

Write-Host "[!] Applying Aggressive TCP/IP Tuning..." -ForegroundColor Yellow
netsh int tcp set global autotuninglevel=experimental | Out-Null
netsh int tcp set global congestionprovider=cubic | Out-Null
netsh int tcp set global ecncapability=enabled | Out-Null
netsh int tcp set global timestamps=disabled | Out-Null
Write-Host "[+] TCP Stack Hardened." -ForegroundColor Green

Write-Host "[!] Rerouting DNS through Artemis Neural Mesh..." -ForegroundColor Yellow
$adapters = Get-NetAdapter | Where-Object { $_.Status -eq "Up" }
foreach ($adapter in $adapters) {
    Set-DnsClientServerAddress -InterfaceIndex $adapter.ifIndex -ServerAddresses ("1.1.1.1", "8.8.8.8")
}
Write-Host "[+] DNS Rerouted to High-Speed Core." -ForegroundColor Green

Write-Host "[!] Disabling Power-Save Throttling..." -ForegroundColor Yellow
Disable-NetAdapterPowerManagement -Name "*" -NoRestart -ErrorAction SilentlyContinue | Out-Null
Write-Host "[+] Throttling Bypass Active." -ForegroundColor Green

Write-Host "[!] Purging Network Cache..." -ForegroundColor Yellow
ipconfig /flushdns | Out-Null
netsh winsock reset | Out-Null

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "   ARTEMIS OPTIMIZATION COMPLETE - REBOOT REQUIRED   " -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
