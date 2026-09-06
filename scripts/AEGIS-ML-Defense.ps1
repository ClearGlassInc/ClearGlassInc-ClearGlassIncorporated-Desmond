# Adversarial ML Defense Function

function Invoke-AegisMLDefense {
    <#
    .SYNOPSIS
        Adversarial ML Defense Layer (AEGIS-ML v2)
    .DESCRIPTION
        Sanitizes and analyzes input strings prior to ML inference to block
        prompt injection, overly large payloads, and low-entropy gibberish.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]
        [string]$InputString,
       
        [string]$ModelPath = "C:\Models\default.onnx",
        [int]$MaxLen = 2048,
        [string]$LogPath = "C:\Logs\adversarial_defense.log"
    )
    # 1. Setup Logging Directory
    $logDir = Split-Path $LogPath
    if (!(Test-Path $logDir)) { New-Item $logDir -ItemType Directory -Force | Out-Null }
    if (!(Test-Path $LogPath)) { New-Item $LogPath -ItemType File -Force | Out-Null }
    # 2. Model Integrity Check
    if (Test-Path $ModelPath) {
        $mHash = (Get-FileHash $ModelPath -Algorithm SHA256).Hash
        "$(Get-Date -Format o) MODEL_OK | Hash:$mHash" | Out-File -FilePath $LogPath -Append -NoClobber
    } else {
        Write-Error "CRITICAL: Model missing at $ModelPath"
        exit 2
    }
    # 3. Input Sanitization
    # Strips potentially dangerous characters (keeps standard text, punctuation, and common symbols)
    $clean = ($InputString -replace '[^\w\s\.\,\-\:\;\/\@\#\?\!]', '').Trim()
    if ($clean.Length -eq 0) {
        "$(Get-Date -Format o) BLOCKED | Reason: Empty after sanitization" | Out-File $LogPath -Append
        throw "Input is empty or invalid."
    }
    # 4. True Shannon Entropy Calculation
    # Measures the unpredictability/randomness of the text to catch spam/gibberish
    $len = $clean.Length
    $entropy = 0
    $groups = $clean.ToCharArray() | Group-Object
    foreach ($g in $groups) {
        $p = $g.Count / $len
        $entropy -= $p * [Math]::Log2($p)
    }
    # 5. Anomaly & Injection Detection
    # Case-insensitive blocklist for common injection vectors
    $blockPattern = '(?i)(eval\(|base64|script\>|exec\(|cmd\.exe|powershell|system\()'
   
    # Heuristics: Length threshold, minimum entropy for natural language (usually ~3.0 - 5.0), and blocklist
    if ($clean.Length -gt $MaxLen -or $entropy -lt 2.5 -or $clean -match $blockPattern) {
        "$(Get-Date -Format o) BLOCKED | Len:$($clean.Length) | Entropy:$([math]::Round($entropy, 2))" | Out-File $LogPath -Append
        Write-Warning "Input blocked by AEGIS-ML constraints."
        exit 1
    }
    # 6. Audit Hash for Tracking
    $bytes = [Text.Encoding]::UTF8.GetBytes($clean)
    $stream = [IO.MemoryStream]::new($bytes)
    $hash = (Get-FileHash -InputStream $stream -Algorithm SHA256).Hash
    $stream.Close()
    "$(Get-Date -Format o) INFER_ALLOW | Hash:$hash | Len:$($clean.Length) | Entropy:$([math]::Round($entropy, 2))" | Out-File $LogPath -Append
   
    # Output the safe, sanitized string to be passed to the model
    return $clean
}
# Example Usage:
# $safeInput = Invoke-AegisMLDefense -InputString "Analyze this standard text log."
# Write-Host "Cleared Input: $safeInput"