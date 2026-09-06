Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Log {
    param(
        [Parameter(Mandatory = $true)][string]$Message,
        [ValidateSet("INFO","ERROR","WARN")][string]$Level = "INFO"
    )

    try {
        $logsDir = Join-Path -Path (Get-Location) -ChildPath "logs"
        if (-not (Test-Path -LiteralPath $logsDir)) {
            New-Item -ItemType Directory -Path $logsDir | Out-Null
        }
        $logFile = Join-Path -Path $logsDir -ChildPath ("automation-{0}.log" -f (Get-Date).ToUniversalTime().ToString("yyyyMM"))
        $utcTs = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        $line = "[{0}] [{1}] {2}" -f $utcTs, $Level, $Message
        Add-Content -Path $logFile -Value $line -Encoding ASCII
        Write-Output $line
    }
    catch {
        Write-Error "Failed to write audit log: $($_.Exception.Message)"
        throw
    }
}

function Invoke-External {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [switch]$IgnoreExitCode
    )

    try {
        Write-Log -Message ("Executing command: {0}" -f $Command)
        $output = & bash -lc "$Command" 2>&1
        $exitCode = $LASTEXITCODE
        if (-not $IgnoreExitCode -and $exitCode -ne 0) {
            throw "Command failed with exit code $exitCode. Output: $($output -join [Environment]::NewLine)"
        }
        return [PSCustomObject]@{
            Output = $output
            ExitCode = $exitCode
        }
    }
    catch {
        Write-Log -Level "ERROR" -Message ("External command error: {0}" -f $_.Exception.Message)
        throw
    }
}

function Get-IndexHash {
    param([Parameter(Mandatory = $true)][string]$Path)
    try {
        if (-not (Test-Path -LiteralPath $Path)) {
            throw "index.html not found at $Path"
        }
        return (Get-FileHash -Algorithm SHA256 -Path $Path).Hash
    }
    catch {
        Write-Log -Level "ERROR" -Message ("Failed to hash index.html: {0}" -f $_.Exception.Message)
        throw
    }
}

function Get-FeatureBranchName {
    return "auto/sync-{0}" -f (Get-Date).ToString("yyyyMMdd-HHmm")
}

$script:RepoRoot = (Get-Location).Path
$script:IndexPath = Join-Path -Path $script:RepoRoot -ChildPath "index.html"
$script:ProtectedHash = ""
$script:ProtectedInitialized = $false

function Ensure-RepoRoot {
    try {
        if (-not (Test-Path -LiteralPath (Join-Path $script:RepoRoot ".git"))) {
            throw "Current directory is not a git repository root: $script:RepoRoot"
        }
        foreach ($f in @("index.html","CNAME",".nojekyll")) {
            if (-not (Test-Path -LiteralPath (Join-Path $script:RepoRoot $f))) {
                throw "Required protected file missing: $f"
            }
        }
    }
    catch {
        Write-Log -Level "ERROR" -Message $_.Exception.Message
        throw
    }
}

function Assert-ProtectedUnchanged {
    try {
        if (-not $script:ProtectedInitialized) {
            throw "Pre-flight hash not initialized. Run option 1 first."
        }
        $current = Get-IndexHash -Path $script:IndexPath
        if ($current -ne $script:ProtectedHash) {
            Write-Log -Level "ERROR" -Message "index.html hash changed. Initiating rollback."
            Invoke-Rollback -Force
            throw "Protected file index.html changed. Rollback completed. Aborting operation."
        }
        Write-Log -Message "Protected hash verification passed."
    }
    catch {
        Write-Log -Level "ERROR" -Message $_.Exception.Message
        throw
    }
}

function Invoke-PreFlight {
    try {
        Ensure-RepoRoot

        foreach ($cmd in @("git","gh","python3")) {
            $check = Get-Command $cmd -ErrorAction SilentlyContinue
            if (-not $check) {
                throw "Required command not found on PATH: $cmd"
            }
        }

        $script:ProtectedHash = Get-IndexHash -Path $script:IndexPath
        $script:ProtectedInitialized = $true
        Write-Log -Message ("Captured pre-flight index.html SHA256: {0}" -f $script:ProtectedHash)

        Invoke-External -Command "git fetch origin"
        Invoke-External -Command "git checkout main"
        Invoke-External -Command "git pull --rebase origin main"

        Assert-ProtectedUnchanged
        Write-Log -Message "Pre-flight completed successfully."
    }
    catch {
        Write-Log -Level "ERROR" -Message ("Pre-flight failed: {0}" -f $_.Exception.Message)
        throw
    }
}

function Invoke-Stage {
    try {
        Assert-ProtectedUnchanged
        Invoke-External -Command "git restore --staged index.html CNAME .nojekyll" -IgnoreExitCode
        Invoke-External -Command "git add --all -- ':!index.html' ':!CNAME' ':!.nojekyll' ':!.github/workflows/**'"
        Invoke-External -Command "git restore --staged index.html CNAME .nojekyll" -IgnoreExitCode
        $status = Invoke-External -Command "git status --short"
        Write-Output ($status.Output -join [Environment]::NewLine)
        Assert-ProtectedUnchanged
        Write-Log -Message "Staging completed with protected exclusions."
    }
    catch {
        Write-Log -Level "ERROR" -Message ("Stage failed: {0}" -f $_.Exception.Message)
        throw
    }
}

function Invoke-Commit {
    try {
        Assert-ProtectedUnchanged
        $defaultMsg = "auto: sync working assets {0}" -f (Get-Date).ToString("yyyy-MM-dd")
        $commitMsg = Read-Host "Enter commit message or press Enter for default"
        if ([string]::IsNullOrWhiteSpace($commitMsg)) {
            $commitMsg = $defaultMsg
        }
        $diff = Invoke-External -Command "git diff --cached --name-only"
        if (-not $diff.Output -or [string]::IsNullOrWhiteSpace(($diff.Output -join ""))) {
            throw "No staged changes to commit."
        }
        Invoke-External -Command ("git commit -m ""{0}""" -f ($commitMsg -replace '"','\"'))
        Assert-ProtectedUnchanged
        Write-Log -Message ("Commit completed: {0}" -f $commitMsg)
    }
    catch {
        Write-Log -Level "ERROR" -Message ("Commit failed: {0}" -f $_.Exception.Message)
        throw
    }
}

function Invoke-PushAndPR {
    try {
        Assert-ProtectedUnchanged

        $auth = Invoke-External -Command "gh auth status" -IgnoreExitCode
        if ($auth.ExitCode -ne 0) {
            throw "GitHub CLI is not authenticated. Run: gh auth login"
        }

        $branch = Get-FeatureBranchName
        Invoke-External -Command ("git checkout -b ""{0}""" -f $branch)
        Invoke-External -Command ("git push -u origin ""{0}""" -f $branch)

        $title = "auto: sync working assets"
        $body = "Automated sync from ClearGlass automation script. Protected files excluded."
        Invoke-External -Command ("gh pr create --base main --head ""{0}"" --title ""{1}"" --body ""{2}"" --no-maintainer-edit" -f $branch, $title, $body)

        Assert-ProtectedUnchanged
        Write-Log -Message ("Push and PR creation completed on branch: {0}" -f $branch)
    }
    catch {
        Write-Log -Level "ERROR" -Message ("Push/PR failed: {0}" -f $_.Exception.Message)
        throw
    }
}

function Invoke-DeployCheck {
    try {
        Assert-ProtectedUnchanged
        $response = Invoke-External -Command "curl -sS -o /dev/null -w '%{http_code}' https://www.clearglassinc.com"
        $httpCode = ($response.Output | Select-Object -Last 1).ToString().Trim()
        if ($httpCode -ne "200") {
            throw "Deployment check failed. HTTP status code: $httpCode"
        }
        Assert-ProtectedUnchanged
        Write-Log -Message "Deploy check passed. HTTP 200 confirmed and protected hash intact."
    }
    catch {
        Write-Log -Level "ERROR" -Message ("Deploy check failed: {0}" -f $_.Exception.Message)
        throw
    }
}

function Invoke-Rollback {
    param([switch]$Force)
    try {
        if (-not $Force) {
            $confirm = Read-Host "Type YES to confirm rollback to origin/main"
            if ($confirm -ne "YES") {
                Write-Log -Level "WARN" -Message "Rollback canceled by user."
                return
            }
        }
        Invoke-External -Command "git fetch origin"
        Invoke-External -Command "git reset --hard origin/main"
        if (Test-Path -LiteralPath $script:IndexPath) {
            $script:ProtectedHash = Get-IndexHash -Path $script:IndexPath
            $script:ProtectedInitialized = $true
        }
        Write-Log -Message "Rollback completed to origin/main."
    }
    catch {
        Write-Log -Level "ERROR" -Message ("Rollback failed: {0}" -f $_.Exception.Message)
        throw
    }
}

function Show-Menu {
    Write-Output ""
    Write-Output "ClearGlass Automation Menu"
    Write-Output "1. PRE-FLIGHT"
    Write-Output "2. STAGE NON-PROTECTED CHANGES"
    Write-Output "3. COMMIT"
    Write-Output "4. PUSH TO FEATURE BRANCH AND OPEN PR"
    Write-Output "5. DEPLOY CHECK"
    Write-Output "6. ROLLBACK"
    Write-Output "7. AUDIT LOG STATUS"
    Write-Output "0. EXIT"
}

function Show-AuditStatus {
    try {
        $logsDir = Join-Path -Path $script:RepoRoot -ChildPath "logs"
        if (-not (Test-Path -LiteralPath $logsDir)) {
            Write-Output "No logs directory found."
            return
        }
        $logFile = Join-Path -Path $logsDir -ChildPath ("automation-{0}.log" -f (Get-Date).ToUniversalTime().ToString("yyyyMM"))
        if (-not (Test-Path -LiteralPath $logFile)) {
            Write-Output "No current month log file found."
            return
        }
        Get-Content -Path $logFile -Tail 25
    }
    catch {
        Write-Log -Level "ERROR" -Message ("Audit status failed: {0}" -f $_.Exception.Message)
        throw
    }
}

try {
    Ensure-RepoRoot
    Write-Log -Message "Automation script started."
}
catch {
    Write-Error $_.Exception.Message
    exit 1
}

while ($true) {
    try {
        Show-Menu
        $choice = Read-Host "Select an option"
        switch ($choice) {
            "1" { Invoke-PreFlight }
            "2" { Invoke-Stage }
            "3" { Invoke-Commit }
            "4" { Invoke-PushAndPR }
            "5" { Invoke-DeployCheck }
            "6" { Invoke-Rollback }
            "7" { Show-AuditStatus }
            "0" {
                Write-Log -Message "Automation script exited by user."
                break
            }
            default {
                Write-Output "Invalid selection."
            }
        }
    }
    catch {
        Write-Output ("Operation failed: {0}" -f $_.Exception.Message)
    }
}
