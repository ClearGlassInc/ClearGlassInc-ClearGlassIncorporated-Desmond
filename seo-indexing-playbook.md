# ClearGlassInc SEO Indexing Playbook

This playbook separates legitimate indexing from black-hat SEO automation.
ClearGlassInc should never use scripts that spam links across forums, comment
sections, directories, or unrelated websites. Those tactics create spam signals,
damage trust, and can suppress discovery instead of improving it.

## Supported indexing workflow

1. Keep `sitemap.xml` current and reachable at `https://www.clearglassinc.com/sitemap.xml`.
2. Keep `robots.txt` advertising the sitemap with a `Sitemap:` directive.
3. Run `scripts/Invoke-SitemapPing.ps1` after meaningful site updates to notify Bing.
4. Submit the same sitemap manually in Google Search Console because Google's public ping endpoint was retired in 2024.
5. Improve ranking through useful page content, accurate metadata, fast loading, internal links, and reputable real-world references.

## PowerShell usage

```powershell
pwsh -File scripts/Invoke-SitemapPing.ps1
```

The script sends one Bing sitemap ping and exits with a non-zero code if Bing is
unreachable or returns an unexpected status. It does not guarantee ranking; it
only requests crawl discovery.

## Offline validation

```bash
python scripts/validate_sitemap_ping.py
```

The validator checks that the sitemap exists, `robots.txt` points to it, and the
PowerShell script uses the approved Bing endpoint without referencing Google's
retired ping endpoint or prohibited spam-style SEO automation.
