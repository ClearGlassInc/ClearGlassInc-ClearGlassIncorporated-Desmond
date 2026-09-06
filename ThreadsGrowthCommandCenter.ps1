<#
.SYNOPSIS
    Builds an ethical, manual Threads growth command center for ClearGlassInc Artemis.
.DESCRIPTION
    Creates local folders, CSV trackers, draft post templates, a daily operating plan,
    and an HTML dashboard for a Threads/Instagram growth workflow. The script is
    intentionally manual-only: it does not log in, scrape, auto-follow, auto-like,
    auto-comment, auto-post, mass-message, or store credentials.
.EXAMPLE
    pwsh -ExecutionPolicy Bypass -File .\ThreadsGrowthCommandCenter.ps1 -OpenDashboard
.EXAMPLE
    pwsh -ExecutionPolicy Bypass -File .\ThreadsGrowthCommandCenter.ps1 -BrandName "MyBrand" -Niche "SaaS security" -RootPath "C:\Growth" -OpenDashboard
#>
[CmdletBinding()]
param(
    [string]$BrandName = 'ClearGlassInc Artemis',
    [string]$Niche = 'AI security, intelligence systems, crypto discipline, and operational sovereignty',
    [string]$RootPath = (Join-Path (Get-Location) 'ThreadsGrowthCommandCenter'),
    [switch]$OpenDashboard
)

Set-StrictMode -Version Latest
THREAT & GROWTH BRIEF - $today
TARGET: $BrandName
SECTOR: $Niche

THE RULES OF HIGH-VELOCITY MANUAL GROWTH:
1. PUBLISH 3X TODAY. Morning, Afternoon, Evening.
2. 40 REPLIES MINIMUM. Target relevant big accounts manually. Be the best reply in their thread.
3. RUTHLESS PRUNING. If yesterday's format tanked twice, kill it and rotate.

EXECUTION BLOCKS:
[ ] 08:00 - Post 1 (High-Signal / Contrarian) + 15 manual replies
[ ] 13:00 - Post 2 (Proof / Screenshot / Result) + 15 manual replies
[ ] 19:00 - Post 3 (Short insight / Lesson) + 10 manual replies

ENGAGEMENT PROTOCOL:
- Never say "Great post!"
- Add missing context, politely disagree, or contribute a sharper useful truth.
- Steal attention ethically by being useful, specific, and manually present.

EVALUATE AND ADAPT:
- What is the Engagement Rate (ER) of yesterday's top post?
- If ER < 2%, the hook was weak. Fix it.
- If the same format fails twice, mark it Killed in Analytics/FormatReview.csv.

COMPLIANCE LINE:
- Zero botting. Zero scraping. Zero fake engagement. Zero mass DMs. No credentials in this folder.
"@
}

function Invoke-DailyWorkflow {
    Initialize-Folders
    if (-not (Test-Path -LiteralPath $CalendarPath)) { Initialize-Workspace }

    $today = Get-Date -Format "yyyy-MM-dd"
    $dailyPlanPath = Join-Path $Folders.DailyPlans "DailyPlan_$today.txt"
    New-DailyPlan | Out-File -LiteralPath $dailyPlanPath -Encoding UTF8

    $calendar = Import-Csv -LiteralPath $CalendarPath
    $todayRows = @($calendar | Where-Object { $_.Date -eq $today })
    if ($todayRows.Count -eq 0) { $todayRows = @($calendar | Select-Object -First 3) }

    foreach ($row in $todayRows) {
        $safeTopic = ConvertTo-SafeFileName -Text $row.Topic
        $draftPath = Join-Path $Folders.Drafts "$today`_$safeTopic.txt"
        if (-not (Test-Path -LiteralPath $draftPath)) {
            New-PostDraft -Topic $row.Topic -Pillar $row.Pillar -Format $row.Format | Out-File -LiteralPath $draftPath -Encoding UTF8
        }
    }
    Write-Status "War Room prepared for $today." "Green"
}

function Add-KpiEntry {
    Initialize-Folders
    if (-not (Test-Path -LiteralPath $KpiPath)) { Initialize-Workspace }
    Backup-FileSafe -Path $KpiPath

    $row = [pscustomobject]@{
        Date = Get-Date -Format "yyyy-MM-dd"
        Followers = $Followers
        Posts = $Posts
        Replies = $Replies
        Likes = $Likes
        Reposts = $Reposts
        Impressions = $Impressions
        ProfileVisits = $ProfileVisits
        Notes = $Notes
    }
    Add-CsvRow -Path $KpiPath -Row $row
    Write-Status "Telemetry logged." "Green"
}

function Convert-RowsToHtmlTable {
    param([array]$Rows, [int]$MaxRows = 10)
    if ($null -eq $Rows -or $Rows.Count -eq 0) { return "<p>No data available.</p>" }
    $selectedRows = @($Rows | Select-Object -First $MaxRows)
    $headers = $selectedRows[0].PSObject.Properties.Name
    $html = "<table><thead><tr>"
    foreach ($header in $headers) { $html += "<th>$(Encode-Html $header)</th>" }
    $html += "</tr></thead><tbody>"
    foreach ($row in $selectedRows) {
        $html += "<tr>"
        foreach ($header in $headers) { $html += "<td>$(Encode-Html $row.$header)</td>" }
        $html += "</tr>"
    }
    $html += "</tbody></table>"
    return $html
}

function New-Dashboard {
    param([switch]$Launch)
    Initialize-Folders
    if (-not (Test-Path -LiteralPath $CalendarPath) -or -not (Test-Path -LiteralPath $KpiPath)) { Initialize-Workspace }

    $calendar = @(Import-Csv -LiteralPath $CalendarPath)
    $kpis = @(Import-Csv -LiteralPath $KpiPath)
    $formats = @(Import-Csv -LiteralPath $FormatReviewPath)

    $latestKpi = $kpis | Select-Object -Last 1
    $upcoming = @($calendar | Where-Object { [datetime]$_.Date -ge (Get-Date).Date } | Select-Object -First 10)
    $recentKpis = @($kpis | Select-Object -Last 10)

    $totalPosts = ($kpis | ForEach-Object { [int]$_.Posts } | Measure-Object -Sum).Sum
    $totalReplies = ($kpis | ForEach-Object { [int]$_.Replies } | Measure-Object -Sum).Sum
    $totalImpressions = ($kpis | ForEach-Object { [int]$_.Impressions } | Measure-Object -Sum).Sum

    $calendarTable = Convert-RowsToHtmlTable -Rows $upcoming -MaxRows 10
    $kpiTable = Convert-RowsToHtmlTable -Rows $recentKpis -MaxRows 10
    $formatTable = Convert-RowsToHtmlTable -Rows $formats -MaxRows 10
    $safeBrand = Encode-Html $BrandName
    $safeNiche = Encode-Html $Niche

    $html = @"
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>$safeBrand Command Center V3</title>
    <style>
        :root { --bg: #09090b; --card: #18181b; --accent: #dc2626; --text: #f4f4f5; --muted: #a1a1aa; --border: #27272a; }
        body { font-family: Inter, Arial, sans-serif; background: var(--bg); color: var(--text); padding: 40px; margin: 0; }
        h1, h2 { color: #fff; text-transform: uppercase; letter-spacing: 1px; }
        h1 { border-bottom: 2px solid var(--accent); display: inline-block; padding-bottom: 10px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .card { background: var(--card); border: 1px solid var(--border); border-left: 4px solid var(--accent); padding: 24px; border-radius: 6px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        .metric { font-size: 38px; font-weight: 900; margin-top: 10px; color: #fff; }
        .label { color: var(--muted); font-size: 13px; text-transform: uppercase; font-weight: bold; letter-spacing: 0.5px; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; background: var(--card); }
        th, td { border: 1px solid var(--border); padding: 12px; text-align: left; }
        th { background: #202024; color: var(--muted); text-transform: uppercase; font-size: 12px; }
        td { color: #e4e4e7; }
        .truth { border-left: 4px solid var(--accent); padding-left: 16px; font-size: 18px; font-weight: bold; color: #fff; font-style: italic; }
        .compliance { color: #fecaca; font-weight: 800; }
    </style>
</head>
<body>
    <h1>SYSTEM V3: $safeBrand</h1>
    <p><strong>Sector:</strong> $safeNiche</p>
    <p class="compliance">Manual-only: zero botting, zero scraping, zero fake engagement, zero mass DMs, zero credential storage.</p>
    <div class="grid">
        <div class="card"><div class="label">Total Followers</div><div class="metric">$(Encode-Html $latestKpi.Followers)</div></div>
        <div class="card"><div class="label">Posts Fired</div><div class="metric">$totalPosts</div></div>
        <div class="card"><div class="label">Replies Deployed</div><div class="metric">$totalReplies</div></div>
        <div class="card"><div class="label">Total Impressions</div><div class="metric">$totalImpressions</div></div>
    </div>
    <h2>The Standard</h2>
    <p class="truth">If it is not generating replies, reposts, saves, or profile visits, it is noise. Kill the format after two failures and try again tomorrow.</p>
    <h2>Upcoming Firepower</h2>
    $calendarTable
    <h2>Telemetry Logs</h2>
    $kpiTable
    <h2>Format Kill List</h2>
    $formatTable
</body>
</html>
"@
    $html | Out-File -LiteralPath $DashboardPath -Encoding UTF8
    Write-Status "Aggressive UI Dashboard compiled: $DashboardPath" "Green"
    if ($Launch) { Start-Process $DashboardPath }
}

switch ($Mode) {
    "Init"      { Initialize-Workspace }
    "Daily"     { Invoke-DailyWorkflow }
    "AddKPI"    { Add-KpiEntry }
    "Dashboard" { New-Dashboard -Launch:$OpenDashboard }
    "All"       { Initialize-Workspace; Invoke-DailyWorkflow; New-Dashboard -Launch:$OpenDashboard }
}
Write-Host ""
Write-Status "V3 Execution Complete. Go to work." "Red"
$ErrorActionPreference = 'Stop'

function New-DirectoryIfMissing {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

function Write-FileIfMissing {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Content
    )
    if (-not (Test-Path -LiteralPath $Path)) {
        $Content | Set-Content -LiteralPath $Path -Encoding UTF8
    }
}

function ConvertTo-HtmlEncodedText {
    param([Parameter(Mandatory = $true)][string]$Value)
    return [System.Net.WebUtility]::HtmlEncode($Value)
}

function New-ThreadsHookLibrary {
    return @(
        'Most brands do not need more noise. They need a system that compounds trust.',
        'The fastest way to look serious online is to show proof of work before opinions.',
        'A clean operating rhythm beats a viral post you cannot repeat.',
        'Security, revenue, and reputation all break when nobody owns the checklist.',
        'If your content cannot survive a compliance review, it is not an asset.',
        'Discipline is the algorithm most people refuse to run.',
        'Crypto rewards patience, records, and risk control more than adrenaline.',
        'AI is only powerful when the workflow around it is measurable.',
        'A founder with a documented system is harder to ignore.',
        'The internet trusts receipts, not declarations.'
    )
}

function New-DraftBody {
    param(
        [Parameter(Mandatory = $true)][string]$Hook,
        [Parameter(Mandatory = $true)][string]$BrandName,
        [Parameter(Mandatory = $true)][string]$Niche,
        [Parameter(Mandatory = $true)][string]$Pillar,
        [Parameter(Mandatory = $true)][int]$Index
    )

    return @"
$Hook

Core point:
$BrandName is building around $Niche. The point is not to post randomly; the point is to publish proof, operating lessons, and decision frameworks that make the brand easier to trust.

Proof:
Today I am documenting pillar $Pillar with a repeatable workflow: idea -> evidence -> useful takeaway -> manual conversation.

Takeaway:
If the content cannot help a real operator think more clearly, it is not ready.

CTA:
If you are building in $Niche, save this and compare it against your own system today.

Manual review checklist:
[ ] No hype claim
[ ] No guaranteed income language
[ ] No spam, scraping, mass DM, or fake engagement tactic
[ ] Includes one proof point or concrete lesson
[ ] Ready to post manually on Threads

Draft ID: THREADS-DRAFT-$('{0:D2}' -f $Index)
"@
}

function Initialize-ThreadsGrowthCommandCenter {
    param(
        [Parameter(Mandatory = $true)][string]$BasePath,
        [Parameter(Mandatory = $true)][string]$BrandName,
        [Parameter(Mandatory = $true)][string]$Niche
    )

    foreach ($folder in @('Drafts', 'Calendars', 'Analytics', 'Engagement', 'DailyPlans', 'Reports')) {
        New-DirectoryIfMissing -Path (Join-Path $BasePath $folder)
    }

    $calendarPath = Join-Path $BasePath 'Calendars/ContentCalendar.csv'
    Write-FileIfMissing -Path $calendarPath -Content @'
Date,Pillar,Topic,Format,CTA,Status,Notes
2026-07-06,Authority,AI security operating checklist,Text post,Save this checklist,Draft,Manual post only
2026-07-07,Business,ClearGlassInc proof-of-work update,Mini-thread,Reply with the system you are building,Draft,Add real proof before posting
2026-07-08,Mindset,Discipline as infrastructure,Text post,Bookmark for daily review,Draft,Keep practical
2026-07-09,Crypto,Risk control beats hype,Text post,Track your rules before your wins,Draft,No financial promises
2026-07-10,Operations,Daily command rhythm,Checklist,Steal this operating rhythm,Draft,Manual engagement after posting
'@

    $kpiPath = Join-Path $BasePath 'Analytics/ThreadsKPITracker.csv'
    Write-FileIfMissing -Path $kpiPath -Content 'Date,Followers,Posts,Replies,Likes,Reposts,Impressions,ProfileVisits,Notes'

    $engagementPath = Join-Path $BasePath 'Engagement/EngagementTracker.csv'
    Write-FileIfMissing -Path $engagementPath -Content 'Date,Creator,CreatorTopic,YourComment,ResponseReceived,FollowUpDate,Outcome,Notes'

    $hooks = New-ThreadsHookLibrary
    $pillars = @('Authority', 'Business', 'Mindset', 'Crypto', 'Operations')
    for ($i = 1; $i -le 10; $i++) {
        $hook = $hooks[($i - 1) % $hooks.Count]
        $pillar = $pillars[($i - 1) % $pillars.Count]
        $draftPath = Join-Path $BasePath ("Drafts/THREADS-DRAFT-{0:D2}.txt" -f $i)
        Write-FileIfMissing -Path $draftPath -Content (New-DraftBody -Hook $hook -BrandName $BrandName -Niche $Niche -Pillar $pillar -Index $i)
    }

    $today = (Get-Date).ToString('yyyy-MM-dd')
    $dailyPlanPath = Join-Path $BasePath "DailyPlans/DailyPlan_$today.txt"
    Write-FileIfMissing -Path $dailyPlanPath -Content @"
$BrandName Threads Daily Growth Plan — $today

Niche:
$Niche

Non-negotiables:
[ ] Publish 2 original manual posts from Drafts or Calendar
[ ] Leave 15 thoughtful strategic replies by hand
[ ] Study 5 competitor or peer posts and write one lesson each
[ ] Update Analytics/ThreadsKPITracker.csv
[ ] Update Engagement/EngagementTracker.csv
[ ] Write one improvement note before ending the day

Rules:
- No bots, scraping, follow/unfollow, fake engagement, engagement pods, or mass DMs.
- No passwords, cookies, API keys, or session tokens in this folder.
- Use proof, useful thinking, and real replies. Manual review always wins.
"@

    $safeBrand = ConvertTo-HtmlEncodedText -Value $BrandName
    $safeNiche = ConvertTo-HtmlEncodedText -Value $Niche
    $dashboardPath = Join-Path $BasePath 'Reports/ThreadsGrowthDashboard.html'
    Write-FileIfMissing -Path $dashboardPath -Content @"
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>$safeBrand Threads Growth Dashboard</title>
  <style>
    body { font-family: Inter, Segoe UI, Arial, sans-serif; margin: 0; background: #09090b; color: #f4f4f5; }
    main { max-width: 1100px; margin: 0 auto; padding: 40px 24px; }
    .hero { border: 1px solid #27272a; border-radius: 24px; padding: 28px; background: linear-gradient(135deg, #111827, #18181b); }
    h1 { margin-top: 0; font-size: 2.3rem; }
    .grid { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); margin-top: 22px; }
    .card { border: 1px solid #27272a; border-radius: 18px; padding: 18px; background: #111113; }
    a { color: #67e8f9; }
    code { color: #fde68a; }
    .rule { color: #fca5a5; font-weight: 700; }
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>$safeBrand Threads Growth Command Center</h1>
      <p><strong>Brand focus:</strong> $safeNiche</p>
      <p class="rule">Manual-only system: no scraping, spam, fake engagement, credential storage, or automation.</p>
    </section>
    <section class="grid">
      <article class="card"><h2>Drafts</h2><p>10 reusable templates using Hook -> Core point -> Proof -> Takeaway -> CTA.</p><p><code>../Drafts</code></p></article>
      <article class="card"><h2>Calendar</h2><p>5 planned posts across Authority, Business, Mindset, Crypto, and Operations.</p><p><a href="../Calendars/ContentCalendar.csv">Open calendar</a></p></article>
      <article class="card"><h2>Analytics</h2><p>Track followers, posts, replies, likes, reposts, impressions, and profile visits.</p><p><a href="../Analytics/ThreadsKPITracker.csv">Open KPI tracker</a></p></article>
      <article class="card"><h2>Engagement</h2><p>Log manual replies, responses, follow-ups, and outcomes.</p><p><a href="../Engagement/EngagementTracker.csv">Open engagement tracker</a></p></article>
      <article class="card"><h2>Daily Plan</h2><p>Run the daily checklist: 2 posts, 15 replies, 5 analyses, KPI update, improvement note.</p><p><code>../DailyPlans</code></p></article>
      <article class="card"><h2>Operating Principle</h2><p>The script does not grow the account. Consistent proof, relevance, and real conversations do.</p></article>
    </section>
  </main>
</body>
</html>
"@

    return [PSCustomObject]@{
        Root = $BasePath
        Calendar = $calendarPath
        KPITracker = $kpiPath
        EngagementTracker = $engagementPath
        DailyPlan = $dailyPlanPath
        Dashboard = $dashboardPath
    }
}

$result = Initialize-ThreadsGrowthCommandCenter -BasePath $RootPath -BrandName $BrandName -Niche $Niche
$result | Format-List

if ($OpenDashboard) {
    if ($IsWindows) { Invoke-Item -LiteralPath $result.Dashboard }
    elseif ($IsMacOS) { & open $result.Dashboard }
    else { Write-Host "Open dashboard manually: $($result.Dashboard)" -ForegroundColor Yellow }
}
