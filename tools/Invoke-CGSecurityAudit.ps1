#requires -Version 5.1
<#
.SYNOPSIS
    ClearGlass Inc. — read-only security Quick-Audit collector.

.DESCRIPTION
    Performs a NON-INTRUSIVE, READ-ONLY posture review of a Windows endpoint and
    (optionally) public email-security DNS records for a domain, then produces a
    branded HTML findings report used to deliver the ClearGlass "Security Quick-Audit"
    and "Hardening Sprint" engagements.

    This script makes NO configuration changes. It only reads local state and public
    DNS. It is intended to be run by, or with the written authorization of, the owner
    of the system / domain being assessed.

.PARAMETER Domain
    Optional public domain to check email-security records (SPF / DMARC) via public DNS.

.PARAMETER OutputPath
    Folder for the generated HTML report. Defaults to the current directory.

.PARAMETER Confirmed
    Pass -Confirmed to acknowledge you are authorized to assess this system/domain.
    Without it, the script pauses for an interactive authorization confirmation.

.EXAMPLE
    .\Invoke-CGSecurityAudit.ps1 -Domain example.com -Confirmed

.NOTES
    ClearGlass Inc. · Clarity is power · www.clearglassinc.com
    Lawful, consent-based use only. Assess only assets you own or are authorized to assess.
#>
[CmdletBinding()]
param(
    [string]$Domain,
    [string]$OutputPath = (Get-Location).Path,
    [switch]$Confirmed
)

# --- Authorization gate -----------------------------------------------------
if (-not $Confirmed) {
    Write-Host ""
    Write-Host "ClearGlass Security Quick-Audit (read-only)" -ForegroundColor Cyan
    Write-Host "You must be authorized to assess this system/domain." -ForegroundColor Yellow
    $ans = Read-Host "Type 'YES' to confirm you have authorization"
    if ($ans -ne 'YES') { Write-Warning "Authorization not confirmed. Aborting."; return }
}

$findings = New-Object System.Collections.Generic.List[object]
function Add-Finding {
    param([string]$Area,[string]$Check,[ValidateSet('Pass','Review','Gap','Info')]$Status,[string]$Detail)
    $findings.Add([pscustomobject]@{ Area=$Area; Check=$Check; Status=$Status; Detail=$Detail })
}

Write-Host "Collecting local (read-only) signals..." -ForegroundColor Cyan

# --- OS / patch hygiene -----------------------------------------------------
try {
    $os = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
    Add-Finding 'System' 'Operating system' 'Info' "$($os.Caption) (build $($os.BuildNumber))"
    $lastBoot = $os.LastBootUpTime
    Add-Finding 'System' 'Last boot' 'Info' "$lastBoot"
    $hotfix = Get-HotFix -ErrorAction SilentlyContinue | Sort-Object InstalledOn -Descending | Select-Object -First 1
    if ($hotfix) {
        $age = (New-TimeSpan -Start $hotfix.InstalledOn -End (Get-Date)).Days
        $st = if ($age -le 45) { 'Pass' } elseif ($age -le 90) { 'Review' } else { 'Gap' }
        Add-Finding 'Patching' 'Most recent update' $st "Last hotfix $($hotfix.HotFixID) installed ~$age days ago"
    } else { Add-Finding 'Patching' 'Update history' 'Review' 'Could not read hotfix history' }
} catch { Add-Finding 'System' 'OS query' 'Review' $_.Exception.Message }

# --- BitLocker --------------------------------------------------------------
try {
    if (Get-Command Get-BitLockerVolume -ErrorAction SilentlyContinue) {
        $sys = Get-BitLockerVolume -MountPoint $env:SystemDrive -ErrorAction Stop
        $st = if ($sys.ProtectionStatus -eq 'On') { 'Pass' } else { 'Gap' }
        Add-Finding 'Encryption' 'BitLocker on system drive' $st "ProtectionStatus = $($sys.ProtectionStatus)"
    } else { Add-Finding 'Encryption' 'BitLocker' 'Review' 'BitLocker cmdlets unavailable (edition/permissions)' }
} catch { Add-Finding 'Encryption' 'BitLocker' 'Review' $_.Exception.Message }

# --- Microsoft Defender -----------------------------------------------------
try {
    if (Get-Command Get-MpComputerStatus -ErrorAction SilentlyContinue) {
        $mp = Get-MpComputerStatus -ErrorAction Stop
        Add-Finding 'Endpoint protection' 'Real-time protection' ($(if($mp.RealTimeProtectionEnabled){'Pass'}else{'Gap'})) "Enabled = $($mp.RealTimeProtectionEnabled)"
        $sigAge = (New-TimeSpan -Start $mp.AntivirusSignatureLastUpdated -End (Get-Date)).Days
        Add-Finding 'Endpoint protection' 'AV signatures' ($(if($sigAge -le 3){'Pass'}elseif($sigAge -le 7){'Review'}else{'Gap'})) "Updated ~$sigAge days ago"
    } else { Add-Finding 'Endpoint protection' 'Defender status' 'Review' 'Defender cmdlets unavailable' }
} catch { Add-Finding 'Endpoint protection' 'Defender status' 'Review' $_.Exception.Message }

# --- Firewall ---------------------------------------------------------------
try {
    if (Get-Command Get-NetFirewallProfile -ErrorAction SilentlyContinue) {
        Get-NetFirewallProfile -ErrorAction Stop | ForEach-Object {
            Add-Finding 'Network' "Firewall: $($_.Name) profile" ($(if($_.Enabled){'Pass'}else{'Gap'})) "Enabled = $($_.Enabled)"
        }
    }
} catch { Add-Finding 'Network' 'Firewall profiles' 'Review' $_.Exception.Message }

# --- Local administrators ---------------------------------------------------
try {
    $admins = Get-LocalGroupMember -Group 'Administrators' -ErrorAction Stop
    $count = ($admins | Measure-Object).Count
    Add-Finding 'Identity' 'Local administrators' ($(if($count -le 3){'Pass'}else{'Review'})) "$count member(s): $((($admins.Name) -join ', '))"
} catch { Add-Finding 'Identity' 'Local administrators' 'Info' 'Could not enumerate (run as admin for this check)' }

# --- Email security DNS (public, read-only) ---------------------------------
if ($Domain) {
    Write-Host "Checking public email-security records for $Domain..." -ForegroundColor Cyan
    if (Get-Command Resolve-DnsName -ErrorAction SilentlyContinue) {
        try {
            $spf = (Resolve-DnsName -Name $Domain -Type TXT -ErrorAction SilentlyContinue).Strings | Where-Object { $_ -like 'v=spf1*' }
            Add-Finding 'Email security' 'SPF record' ($(if($spf){'Pass'}else{'Gap'})) ($(if($spf){"$spf"}else{'No SPF (v=spf1) TXT record found'}))
        } catch { Add-Finding 'Email security' 'SPF record' 'Review' $_.Exception.Message }
        try {
            $dmarc = (Resolve-DnsName -Name "_dmarc.$Domain" -Type TXT -ErrorAction SilentlyContinue).Strings | Where-Object { $_ -like 'v=DMARC1*' }
            $st = if (-not $dmarc) { 'Gap' } elseif ($dmarc -match 'p=reject|p=quarantine') { 'Pass' } else { 'Review' }
            Add-Finding 'Email security' 'DMARC record' $st ($(if($dmarc){"$dmarc"}else{'No DMARC record found'}))
        } catch { Add-Finding 'Email security' 'DMARC record' 'Review' $_.Exception.Message }
    } else { Add-Finding 'Email security' 'DNS lookups' 'Review' 'Resolve-DnsName unavailable on this host' }
}

# --- Report -----------------------------------------------------------------
$generated = Get-Date -Format 'yyyy-MM-dd HH:mm'
$counts = $findings | Group-Object Status | Select-Object Name,Count
$color = @{ Pass='#0b8f86'; Review='#c98a00'; Gap='#c0392b'; Info='#5b6b7a' }
$rows = ($findings | ForEach-Object {
    $c = $color[$_.Status]
    "<tr><td>$($_.Area)</td><td>$($_.Check)</td><td><span style='color:$c;font-weight:700'>$($_.Status)</span></td><td>$([System.Web.HttpUtility]::HtmlEncode($_.Detail))</td></tr>"
}) -join "`n"

Add-Type -AssemblyName System.Web -ErrorAction SilentlyContinue
$summary = ($counts | ForEach-Object { "$($_.Name): $($_.Count)" }) -join ' &nbsp;·&nbsp; '

$html = @"
<!DOCTYPE html><html><head><meta charset='utf-8'>
<title>ClearGlass Security Quick-Audit — $($env:COMPUTERNAME)</title>
<style>
body{font:14px/1.6 -apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#16202b;max-width:900px;margin:0 auto;padding:32px}
h1{font-size:26px;margin-bottom:4px}.sub{color:#5b6b7a}
.bar{height:4px;background:linear-gradient(90deg,#39d0c3,#0a2230);border-radius:4px;margin:16px 0 22px}
.sum{background:#f4f8fb;border:1px solid #e1e9f0;border-radius:10px;padding:12px 16px;margin-bottom:20px;font-weight:600}
table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:9px 10px;border-bottom:1px solid #eef2f6;vertical-align:top}
th{background:#0a2230;color:#fff;font-size:13px}
.note{background:#eef6ff;border:1px solid #cfe2f7;border-radius:10px;padding:12px 14px;font-size:12px;color:#2c4a66;margin-top:22px}
footer{margin-top:20px;color:#5b6b7a;font-size:12px}
</style></head><body>
<h1>Security Quick-Audit</h1>
<div class='sub'>ClearGlass Inc. · Clarity is power · Host: $($env:COMPUTERNAME)$(if($Domain){" · Domain: $Domain"}) · Generated: $generated</div>
<div class='bar'></div>
<div class='sum'>Summary &nbsp; $summary</div>
<table><thead><tr><th>Area</th><th>Check</th><th>Status</th><th>Detail</th></tr></thead><tbody>
$rows
</tbody></table>
<div class='note'>Read-only assessment — no configuration was changed. <b>Review</b> items warrant a closer look; <b>Gap</b> items are recommended for remediation. This automated collection is a starting point; a ClearGlass Hardening Sprint provides full analysis and prioritized remediation.</div>
<footer>© ClearGlass Inc., Ontario, Canada. Performed under authorization for the assessed system/domain. www.clearglassinc.com/offers/</footer>
</body></html>
"@

$file = Join-Path $OutputPath ("CG-QuickAudit-{0}-{1}.html" -f $env:COMPUTERNAME, (Get-Date -Format 'yyyyMMdd-HHmm'))
$html | Out-File -FilePath $file -Encoding UTF8
Write-Host ""
Write-Host "Report written to: $file" -ForegroundColor Green
Write-Host "Findings: $summary"
return $file
