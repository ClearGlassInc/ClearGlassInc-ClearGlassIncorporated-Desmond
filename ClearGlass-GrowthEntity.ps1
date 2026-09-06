<#
.SYNOPSIS
    ClearGlass Sovereign Growth Entity v1.0 local command system.
.DESCRIPTION
    Scores content opportunities, produces a daily posting plan, exports revenue actions,
    and flags compliance/suppression risks. This is a manual-review planning system only:
    it does not auto-post, scrape, mass-message, store passwords, or bypass platform rules.
#>
[CmdletBinding()]
param(
    [ValidateSet('Sample','Full')]
    [string]$Mode = 'Full',
    [string]$Root = (Join-Path (Get-Location) 'ClearGlassGrowthEntity'),
    [switch]$OpenFolder
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function New-DirectoryIfMissing {
    param([Parameter(Mandatory=$true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

function Write-JsonFile {
    param(
        [Parameter(Mandatory=$true)]$Object,
        [Parameter(Mandatory=$true)][string]$Path
    )
    $Object | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Initialize-GrowthEntity {
    param([Parameter(Mandatory=$true)][string]$BasePath)

    foreach ($folder in @('config','data','exports','reports','logs')) {
        New-DirectoryIfMissing -Path (Join-Path $BasePath $folder)
    }

    $configPath = Join-Path $BasePath 'config/growth_config.json'
    if (-not (Test-Path -LiteralPath $configPath)) {
        Write-JsonFile -Path $configPath -Object ([ordered]@{
            version = '1.0'
            operating_rule = 'Manual review only. No passwords, fake engagement, mass DMs, scraping, or bypass behavior.'
            weights = [ordered]@{
                opportunity = 0.30
                authority = 0.24
                monetization = 0.26
                compliance_risk = -0.12
                suppression_risk = -0.08
            }
            compliance_flags = @('guaranteed income','risk-free crypto','mass DM','shadowban bypass','fake engagement','engagement pod','bot followers','scrape users','bypass rate limits')
            offer_tracks = @('audit','buildout','retainer','template','playbook')
            platforms = @('LinkedIn','X','Meta','YouTube','Website','Email')
        })
    }

    $accountsPath = Join-Path $BasePath 'config/accounts.template.json'
    if (-not (Test-Path -LiteralPath $accountsPath)) {
        Write-JsonFile -Path $accountsPath -Object ([ordered]@{
            warning = 'Template only. Do not store passwords, tokens, cookies, or API secrets here.'
            accounts = @(
                [ordered]@{ platform='LinkedIn'; handle=''; role='authority'; posting_window_utc='14:00' },
                [ordered]@{ platform='X'; handle=''; role='distribution'; posting_window_utc='16:00' },
                [ordered]@{ platform='YouTube'; handle=''; role='proof'; posting_window_utc='18:00' }
            )
        })
    }

    $queuePath = Join-Path $BasePath 'data/content_queue.csv'
    if (-not (Test-Path -LiteralPath $queuePath)) {
        @'
id,title,platform,format,topic,hook,offer_track,proof_asset,opportunity,authority,monetization,compliance_risk,suppression_risk,status
CG-001,SMB Cyber Trust Kit Launch,LinkedIn,carousel,cybersecurity,"Most SMB security fails because nobody owns the weekly checklist.",audit,operations/smb_cyber_trust_kit/smb-cyber-trust-kit.md,9,8,8,1,1,ready
CG-002,Artemis Self-Evolving AI Blueprint,X,thread,ai architecture,"A self-improving AI system without approval gates is not strategy. It is liability.",buildout,CLEARGLASSINC_ARTEMIS_PALANTIR_SELF_EVOLVING_AI_IMPLEMENTATION.md,8,9,7,2,2,ready
CG-003,CashPulse Revenue Automation,Website,case-study,automation,"Revenue systems should make the next action obvious before cash gets late.",retainer,deployment/cashpulse/README.md,7,7,9,1,1,ready
'@ | Set-Content -LiteralPath $queuePath -Encoding UTF8
    }

    $ledgerPath = Join-Path $BasePath 'data/revenue_ledger.csv'
    if (-not (Test-Path -LiteralPath $ledgerPath)) {
        'date,lead,source,offer_track,next_action,value_estimate,status,notes' | Set-Content -LiteralPath $ledgerPath -Encoding UTF8
    }

    $postedLog = Join-Path $BasePath 'logs/posted_log.csv'
    if (-not (Test-Path -LiteralPath $postedLog)) {
        'timestamp_utc,content_id,platform,status,operator,notes' | Set-Content -LiteralPath $postedLog -Encoding UTF8
    }
}

function Get-GrowthConfig {
    param([Parameter(Mandatory=$true)][string]$BasePath)
    Get-Content -LiteralPath (Join-Path $BasePath 'config/growth_config.json') -Raw | ConvertFrom-Json
}

function Get-RiskFlags {
    param([string]$Text, [string[]]$Phrases)
    $hits = New-Object System.Collections.Generic.List[string]
    foreach ($phrase in $Phrases) {
        if ($Text -match [regex]::Escape($phrase)) { [void]$hits.Add($phrase) }
    }
    return ($hits -join '; ')
}

function ConvertTo-Number {
    param($Value)
    if ($null -eq $Value -or $Value -eq '') { return 0.0 }
    return [double]$Value
}

function Score-ContentQueue {
    param([Parameter(Mandatory=$true)][string]$BasePath)
    $config = Get-GrowthConfig -BasePath $BasePath
    $queuePath = Join-Path $BasePath 'data/content_queue.csv'
    $rows = Import-Csv -LiteralPath $queuePath
    $phrases = @($config.compliance_flags)
    $weights = $config.weights

    foreach ($row in $rows) {
        $text = ('{0} {1} {2} {3}' -f $row.title,$row.topic,$row.hook,$row.offer_track).ToLowerInvariant()
        $flags = Get-RiskFlags -Text $text -Phrases $phrases
        $flagPenalty = if ([string]::IsNullOrWhiteSpace($flags)) { 0 } else { 2 }
        $complianceRisk = (ConvertTo-Number $row.compliance_risk) + $flagPenalty
        $suppressionRisk = (ConvertTo-Number $row.suppression_risk) + ($(if ($flags) { 1 } else { 0 }))
        $score =
            ((ConvertTo-Number $row.opportunity) * [double]$weights.opportunity) +
            ((ConvertTo-Number $row.authority) * [double]$weights.authority) +
            ((ConvertTo-Number $row.monetization) * [double]$weights.monetization) +
            ($complianceRisk * [double]$weights.compliance_risk) +
            ($suppressionRisk * [double]$weights.suppression_risk)

        [PSCustomObject]@{
            id = $row.id
            title = $row.title
            platform = $row.platform
            format = $row.format
            topic = $row.topic
            hook = $row.hook
            offer_track = $row.offer_track
            proof_asset = $row.proof_asset
            opportunity = $row.opportunity
            authority = $row.authority
            monetization = $row.monetization
            compliance_risk = [math]::Round($complianceRisk,2)
            suppression_risk = [math]::Round($suppressionRisk,2)
            risk_flags = $flags
            growth_score = [math]::Round($score,3)
            status = $row.status
        }
    }
}

function Write-GrowthReports {
    param([Parameter(Mandatory=$true)][string]$BasePath)
    $date = (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd')
    $scored = @(Score-ContentQueue -BasePath $BasePath | Sort-Object -Property growth_score -Descending)

    $scoredPath = Join-Path $BasePath "exports/scored_content_$date.csv"
    $planPath = Join-Path $BasePath "reports/daily_plan_$date.csv"
    $briefPath = Join-Path $BasePath "reports/posting_brief_$date.md"
    $financePath = Join-Path $BasePath "reports/finance_actions_$date.csv"
    $reportPath = Join-Path $BasePath "reports/growth_report_$date.md"

    $scored | Export-Csv -LiteralPath $scoredPath -NoTypeInformation -Encoding UTF8
    $scored | Select-Object -First 5 id,platform,format,title,hook,offer_track,growth_score,risk_flags | Export-Csv -LiteralPath $planPath -NoTypeInformation -Encoding UTF8

    $financeRows = foreach ($item in ($scored | Select-Object -First 5)) {
        [PSCustomObject]@{
            date = $date
            content_id = $item.id
            offer_track = $item.offer_track
            action = "Prepare $($item.offer_track) CTA and manual follow-up list for $($item.platform)."
            value_estimate = switch ($item.offer_track) { 'audit' { 1500 } 'buildout' { 7500 } 'retainer' { 5000 } 'template' { 199 } 'playbook' { 499 } default { 1000 } }
            compliance_review_required = -not [string]::IsNullOrWhiteSpace($item.risk_flags)
        }
    }
    $financeRows | Export-Csv -LiteralPath $financePath -NoTypeInformation -Encoding UTF8

    $top = $scored | Select-Object -First 1
    $flagged = @($scored | Where-Object { -not [string]::IsNullOrWhiteSpace($_.risk_flags) })
    $brief = @()
    $brief += "# ClearGlass Sovereign Growth Entity — Posting Brief $date"
    $brief += ''
    $brief += '## Operating Rule'
    $brief += 'Manual review only. Do not store passwords. Do not use fake engagement, mass DMs, scraping, or bypass behavior.'
    $brief += ''
    $brief += '## Top Move'
    if ($top) { $brief += "- **$($top.platform)** / **$($top.format)**: $($top.title) — score $($top.growth_score)"; $brief += "- Hook: $($top.hook)"; $brief += "- Offer direction: $($top.offer_track)" }
    $brief += ''
    $brief += '## Compliance Flags'
    if ($flagged.Count -eq 0) { $brief += '- No dangerous language detected in the current queue.' } else { foreach ($item in $flagged) { $brief += "- $($item.id): $($item.risk_flags)" } }
    $brief | Set-Content -LiteralPath $briefPath -Encoding UTF8

    $report = @()
    $report += "# ClearGlass Sovereign Growth Entity — Growth Report $date"
    $report += ''
    $report += "- Content scored: $($scored.Count)"
    $report += "- Flagged items: $($flagged.Count)"
    $report += "- Highest score: $($top.growth_score) ($($top.id))"
    $report += "- Revenue actions generated: $($financeRows.Count)"
    $report += ''
    $report += '## Generated Files'
    $report += "- $scoredPath"
    $report += "- $planPath"
    $report += "- $briefPath"
    $report += "- $financePath"
    $report | Set-Content -LiteralPath $reportPath -Encoding UTF8

    [PSCustomObject]@{
        Root = $BasePath
        ScoredContent = $scoredPath
        DailyPlan = $planPath
        PostingBrief = $briefPath
        FinanceActions = $financePath
        GrowthReport = $reportPath
    }
}

Initialize-GrowthEntity -BasePath $Root
if ($Mode -eq 'Sample') {
    Write-Host 'Sample mode initialized the command center and seeded example content.' -ForegroundColor Cyan
}
$result = Write-GrowthReports -BasePath $Root
$result | Format-List

if ($OpenFolder) {
    if ($IsWindows) { Invoke-Item -LiteralPath $Root }
    elseif ($IsMacOS) { & open $Root }
    else { Write-Host "Open folder manually: $Root" -ForegroundColor Yellow }
}
