# ==============================================================================
# Safer Windows GPU & Gaming Tuning Script — Audit-First Edition
# ClearGlassInc Artemis utility script
# Must be executed in an Elevated PowerShell Window (Run as Administrator)
#
# Design goals:
# - Add a safer alternative to the aggressive enthusiast script without removing it.
# - Back up relevant registry hives before any change.
# - Default to low-risk checks and HAGS / power-plan actions only.
# - Keep TDR, SystemProfile, network-throttling, and MMCSS changes opt-in.
# - Log every action and provide a rollback helper.
#
# Example:
#   powershell -ExecutionPolicy Bypass -File .\tools\windows\safe-windows-gpu-tuning.ps1 -ApplyLowRisk
#   powershell -ExecutionPolicy Bypass -File .\tools\windows\safe-windows-gpu-tuning.ps1 -ApplyLowRisk -IncludeExperimentalTweaks
#   powershell -ExecutionPolicy Bypass -File .\tools\windows\safe-windows-gpu-tuning.ps1 -RollbackFrom "$env:USERPROFILE\Desktop\Artemis_GPU_Tuning_Backup_YYYYMMDD_HHMMSS"
# ==============================================================================

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [switch]$ApplyLowRisk,
    [switch]$IncludeTdrDelay,
    [switch]$IncludeExperimentalTweaks,
    [switch]$EnableHags,
    [switch]$DisableHags,
    [string]$RollbackFrom
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-Administrator {
    $principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "This script must be run from an elevated Administrator PowerShell session."
    }
}

function New-BackupFolder {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $folder = Join-Path ([Environment]::GetFolderPath("Desktop")) "Artemis_GPU_Tuning_Backup_$stamp"
    New-Item -ItemType Directory -Path $folder -Force | Out-Null
    return $folder
}

function Write-LogLine {
    param([string]$Message, [string]$Level = "INFO")
    $line = "{0} [{1}] {2}" -f (Get-Date -Format o), $Level, $Message
    Write-Host $line
    if ($script:LogFile) { Add-Content -Path $script:LogFile -Value $line }
}

function Export-RegistryKeyIfPresent {
    param([string]$RegExePath, [string]$OutputFile)
    if (Test-Path ("Registry::{0}" -f $RegExePath)) {
        & reg export $RegExePath $OutputFile /y | Out-Null
        Write-LogLine "Exported $RegExePath to $OutputFile"
    }
    else {
        Write-LogLine "Registry key not present, skipped backup: $RegExePath" "WARN"
    }
}

function Save-CurrentValue {
    param([string]$PsPath, [string]$Name, [string]$SnapshotFile)
    $exists = Test-Path $PsPath
    $value = $null
    if ($exists) {
        $item = Get-ItemProperty -Path $PsPath -Name $Name -ErrorAction SilentlyContinue
        if ($null -ne $item) { $value = $item.$Name }
    }
    [pscustomobject]@{ Path = $PsPath; Name = $Name; Exists = $exists; Value = $value } |
        ConvertTo-Json -Compress | Add-Content -Path $SnapshotFile
}

function Set-DwordValue {
    param([string]$Path, [string]$Name, [UInt32]$Value, [string]$Why)
    if (-not (Test-Path $Path)) { New-Item -Path $Path -Force | Out-Null }
    if ($PSCmdlet.ShouldProcess("$Path::$Name", "Set DWORD $Value ($Why)")) {
        New-ItemProperty -Path $Path -Name $Name -Value $Value -PropertyType DWord -Force | Out-Null
        Write-LogLine "Set $Path::$Name to $Value — $Why"
    }
}

function Set-StringValue {
    param([string]$Path, [string]$Name, [string]$Value, [string]$Why)
    if (-not (Test-Path $Path)) { New-Item -Path $Path -Force | Out-Null }
    if ($PSCmdlet.ShouldProcess("$Path::$Name", "Set string $Value ($Why)")) {
        New-ItemProperty -Path $Path -Name $Name -Value $Value -PropertyType String -Force | Out-Null
        Write-LogLine "Set $Path::$Name to $Value — $Why"
    }
}

function Enable-UltimatePerformancePlan {
    $ultimateGuid = "e9a42b02-d5df-448d-aa00-03f14749eb61"
    $plans = (& powercfg /list) -join "`n"
    if ($plans -match $ultimateGuid) {
        Write-LogLine "Ultimate Performance plan already exists. Activating existing plan."
        & powercfg /setactive $ultimateGuid
        return $ultimateGuid
    }

    Write-LogLine "Ultimate Performance plan not listed. Attempting to duplicate the Windows template."
    $duplicateOutput = (& powercfg -duplicatescheme $ultimateGuid) -join "`n"
    Write-LogLine "powercfg duplicate output: $duplicateOutput"
    $guidMatch = [regex]::Match($duplicateOutput, "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
    if (-not $guidMatch.Success) {
        throw "Could not parse duplicated Ultimate Performance plan GUID from powercfg output. No power plan was activated."
    }
    $newGuid = $guidMatch.Value
    & powercfg /setactive $newGuid
    Write-LogLine "Activated duplicated Ultimate Performance plan: $newGuid"
    return $newGuid
}

function Invoke-Rollback {
    param([string]$Folder)
    if (-not (Test-Path $Folder)) { throw "Rollback folder does not exist: $Folder" }
    Get-ChildItem -Path $Folder -Filter "*.reg" | ForEach-Object {
        Write-Host "Importing rollback file: $($_.FullName)"
        & reg import $_.FullName | Out-Null
    }
    Write-Host "Rollback import complete. Restart Windows to fully apply restored registry state." -ForegroundColor Yellow
}

Assert-Administrator

if ($RollbackFrom) {
    Invoke-Rollback -Folder $RollbackFrom
    return
}

if (-not ($ApplyLowRisk -or $EnableHags -or $DisableHags -or $IncludeTdrDelay -or $IncludeExperimentalTweaks)) {
    Write-Host "No changes requested. Re-run with -ApplyLowRisk, -EnableHags, -DisableHags, -IncludeTdrDelay, or -IncludeExperimentalTweaks." -ForegroundColor Yellow
    Write-Host "Use -WhatIf with any apply flag to preview actions."
    return
}

$script:BackupFolder = New-BackupFolder
$script:LogFile = Join-Path $script:BackupFolder "artemis_gpu_tuning.log"
$SnapshotFile = Join-Path $script:BackupFolder "registry_value_snapshot.jsonl"

$GraphicsPath      = "HKLM:\SYSTEM\CurrentControlSet\Control\GraphicsDrivers"
$SystemProfilePath = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile"
$MMCSSPath         = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games"

Write-LogLine "Backup folder: $script:BackupFolder"
Export-RegistryKeyIfPresent "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\GraphicsDrivers" (Join-Path $script:BackupFolder "GraphicsDrivers_Backup.reg")
Export-RegistryKeyIfPresent "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile" (Join-Path $script:BackupFolder "SystemProfile_Backup.reg")

@(
    @($GraphicsPath, "HwSchMode"),
    @($GraphicsPath, "TdrDelay"),
    @($GraphicsPath, "TdrDdiDelay"),
    @($SystemProfilePath, "SystemResponsiveness"),
    @($SystemProfilePath, "NetworkThrottlingIndex"),
    @($MMCSSPath, "GPU Priority"),
    @($MMCSSPath, "Priority"),
    @($MMCSSPath, "Scheduling Category"),
    @($MMCSSPath, "SFIO Priority")
) | ForEach-Object { Save-CurrentValue -PsPath $_[0] -Name $_[1] -SnapshotFile $SnapshotFile }
Write-LogLine "Saved point-in-time registry value snapshot to $SnapshotFile"

if ($ApplyLowRisk) {
    Write-LogLine "Applying low-risk set: HAGS preference when requested and Ultimate Performance activation with GUID verification."
    [void](Enable-UltimatePerformancePlan)
}

if ($EnableHags -or ($ApplyLowRisk -and -not $DisableHags)) {
    Set-DwordValue -Path $GraphicsPath -Name "HwSchMode" -Value 2 -Why "Enable Hardware-Accelerated GPU Scheduling when supported by GPU/driver/Windows build."
}
elseif ($DisableHags) {
    Set-DwordValue -Path $GraphicsPath -Name "HwSchMode" -Value 1 -Why "Disable Hardware-Accelerated GPU Scheduling for stability testing."
}

if ($IncludeTdrDelay) {
    Write-LogLine "TDR delay changes are troubleshooting-only. They can make real GPU hangs feel longer before Windows recovers." "WARN"
    Set-DwordValue -Path $GraphicsPath -Name "TdrDelay" -Value 10 -Why "Opt-in troubleshooting delay for GPU timeout recovery."
    Set-DwordValue -Path $GraphicsPath -Name "TdrDdiDelay" -Value 10 -Why "Opt-in troubleshooting delay for driver-interface timeout recovery."
}

if ($IncludeExperimentalTweaks) {
    Write-LogLine "Experimental SystemProfile/MMCSS tweaks are not guaranteed to improve modern game latency and may affect audio/capture/background behavior." "WARN"
    Set-DwordValue -Path $SystemProfilePath -Name "SystemResponsiveness" -Value 0 -Why "Opt-in experimental multimedia scheduler setting."
    Set-DwordValue -Path $SystemProfilePath -Name "NetworkThrottlingIndex" -Value 0xffffffff -Why "Opt-in experimental network throttling setting."
    Set-DwordValue -Path $MMCSSPath -Name "GPU Priority" -Value 8 -Why "Opt-in experimental Games task priority."
    Set-DwordValue -Path $MMCSSPath -Name "Priority" -Value 6 -Why "Opt-in experimental Games task priority."
    Set-StringValue -Path $MMCSSPath -Name "Scheduling Category" -Value "High" -Why "Opt-in experimental Games scheduling category."
    Set-StringValue -Path $MMCSSPath -Name "SFIO Priority" -Value "High" -Why "Opt-in experimental Games SFIO priority."
}

Write-LogLine "Complete. Benchmark before/after with the same workload and rollback anything that increases crashes, stutter, or input lag. Restart Windows before final judgment."
Write-Host "Rollback command:" -ForegroundColor Cyan
Write-Host "powershell -ExecutionPolicy Bypass -File .\tools\windows\safe-windows-gpu-tuning.ps1 -RollbackFrom `"$script:BackupFolder`"" -ForegroundColor Cyan
