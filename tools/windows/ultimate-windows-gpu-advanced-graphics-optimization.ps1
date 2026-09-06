# ==============================================================================
# Ultimate Windows GPU & Advanced Graphics Optimization Script — Enthusiast Edition
# ClearGlassInc Artemis utility script
# Must be executed in an Elevated PowerShell Window (Run as Administrator)
# ==============================================================================

# 1. Enforce Administrator Privileges
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "CRITICAL: This script must be run as Administrator! Please close this window, right-click PowerShell, and select 'Run as administrator'."
    Break
}

Write-Host "Unlocking deep system pipelines and extreme GPU latency optimization..." -ForegroundColor Cyan

# 2. Setup Desktop Backup Directory
$BackupFolder = Join-Path ([Environment]::GetFolderPath("Desktop")) "GPU_Maximus_Optimization_Backup"
if (-not (Test-Path $BackupFolder)) {
    New-Item -ItemType Directory -Path $BackupFolder -Force | Out-Null
}
Write-Host "Safety net active. Backups will be saved to: $BackupFolder" -ForegroundColor Yellow

# Define Registry Paths
$GraphicsPath      = "HKLM:\SYSTEM\CurrentControlSet\Control\GraphicsDrivers"
$SystemProfilePath = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile"
$MMCSSPath         = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games"

# 3. Backup Original Settings (If keys exist)
Write-Host "Executing full registry state backup..." -ForegroundColor Gray
if (Test-Path $GraphicsPath) {
    reg export "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\GraphicsDrivers" "$BackupFolder\GraphicsDrivers_Backup.reg" /y | Out-Null
}
if (Test-Path $SystemProfilePath) {
    reg export "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile" "$BackupFolder\SystemProfile_Backup.reg" /y | Out-Null
}

# 4. Apply Advanced Optimization Tweaks
try {
    # Tweak A: Hardware-Accelerated GPU Scheduling (HAGS)
    # Direct VRAM control to the GPU; unlocks DLSS 3+ Frame Generation pipelines.
    Set-ItemProperty -Path $GraphicsPath -Name "HwSchMode" -Value 2 -Force

    # Tweak B: Adjust Timeout Detection and Recovery (TDR) Delays
    # Gives the GPU 10 seconds to finish intensive asset streams before Windows forces a driver crash.
    Set-ItemProperty -Path $GraphicsPath -Name "TdrDelay" -Value 10 -Force
    Set-ItemProperty -Path $GraphicsPath -Name "TdrDdiDelay" -Value 10 -Force

    # Tweak C: Inject and Activate 'Ultimate Performance' Power Plan
    # Disables core-parking and voltage drop-offs across PCIe slots and memory lanes.
    $UltimateGUID = "e9a42b02-d5df-448d-aa00-03f14749eb61"
    & powercfg -duplicatescheme $UltimateGUID | Out-Null
    & powercfg -setactive $UltimateGUID

    # Tweak D: System Responsiveness & Network Throttling Defeat
    # Stops Windows from reserving 20% of CPU cycles for background tasks and stops network card
    # throttling during high-bandwidth 3D gameplay engines.
    Set-ItemProperty -Path $SystemProfilePath -Name "SystemResponsiveness" -Value 0 -Force
    Set-ItemProperty -Path $SystemProfilePath -Name "NetworkThrottlingIndex" -Value 0xffffffff -Force

    # Tweak E: Tune MMCSS & SFIO Thread Scheduling Priorities
    # Maximizes task cycles and prioritizes sequential file input/output (asset streaming from SSDs)
    # directly for active gaming engines.
    if (-not (Test-Path $MMCSSPath)) { New-Item -Path $MMCSSPath -Force | Out-Null }
    Set-ItemProperty -Path $MMCSSPath -Name "GPU Priority" -Value 8 -Force
    Set-ItemProperty -Path $MMCSSPath -Name "Priority" -Value 6 -Force
    Set-ItemProperty -Path $MMCSSPath -Name "Scheduling Category" -Value "High" -Force
    Set-ItemProperty -Path $MMCSSPath -Name "SFIO Priority" -Value "High" -Force

    Write-Host "`n[SUCCESS] Matrix-level system and GPU configurations applied!" -ForegroundColor Green
    Write-Host "[ACTION REQUIRED] Please restart your PC to initialize the high-performance kernel state." -ForegroundColor Green
}
catch {
    Write-Error "An error occurred while modifying advanced registry values: $_"
    Write-Host "To revert completely, run the backup files located in your desktop folder." -ForegroundColor Yellow
}
