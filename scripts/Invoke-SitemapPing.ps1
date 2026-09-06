<#
.SYNOPSIS
  Legitimately notifies Bing that the ClearGlassInc GitHub Pages sitemap should be crawled.

.DESCRIPTION
  This script performs a single standards-aligned sitemap ping for Bing. It does not
  automate link spam, directory submissions, comments, forum posts, or any other
  black-hat SEO behavior. Google retired its public sitemap ping endpoint in 2024;
  submit the sitemap through Google Search Console instead.
#>
[CmdletBinding()]
param(
    [Parameter()]
    [ValidatePattern('^https://')]
    [string]$SitemapUrl = 'https://www.clearglassinc.com/sitemap.xml',

    [Parameter()]
    [int]$TimeoutSec = 20
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Write-Host 'Notifying search engines to crawl your site...' -ForegroundColor Cyan
Write-Host "Sitemap: $SitemapUrl" -ForegroundColor Gray

$encodedSitemap = [System.Uri]::EscapeDataString($SitemapUrl)
$bingPingUrl = "https://www.bing.com/ping?sitemap=$encodedSitemap"

try {
    $response = Invoke-WebRequest -Uri $bingPingUrl -UseBasicParsing -TimeoutSec $TimeoutSec

    if ($response.StatusCode -eq 200) {
        Write-Host "Success: Website pushed to Bing's crawl queue." -ForegroundColor Green
        exit 0
    }

    Write-Host "Warning: Bing returned HTTP $($response.StatusCode)." -ForegroundColor Yellow
    exit 2
} catch {
    Write-Host "Error pushing sitemap to Bing: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally {
    Write-Host ''
    Write-Host 'IMPORTANT GOOGLE UPDATE:' -ForegroundColor Yellow
    Write-Host 'Google retired its automated sitemap ping service in 2024.' -ForegroundColor Gray
    Write-Host 'Use Google Search Console to submit https://www.clearglassinc.com/sitemap.xml manually.' -ForegroundColor Gray
    Write-Host 'This script supports indexing discovery only; it does not guarantee ranking.' -ForegroundColor Gray
}
