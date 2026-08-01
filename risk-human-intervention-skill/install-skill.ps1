<#
.SYNOPSIS
    Install risk-human-intervention skill (complete package v1.4.0) into Codex skills directory.
.DESCRIPTION
    Copies this package to %USERPROFILE%\.codex\skills\risk-human-intervention
    for automatic registration by Codex.
.EXAMPLE
    .\install-skill.ps1
#>

$source = $PSScriptRoot
$dest = Join-Path $env:USERPROFILE ".codex\skills\risk-human-intervention"

if (-not (Test-Path (Join-Path $source "SKILL.md"))) {
    Write-Error "SKILL.md not found next to this script: $source"
    exit 1
}

Write-Host "Installing risk-human-intervention skill (v1.4.0)..." -ForegroundColor Cyan
Write-Host "  From: $source"
Write-Host "  To:   $dest"

New-Item -ItemType Directory -Path $dest -Force | Out-Null
Copy-Item -Path (Join-Path $source "*") -Destination $dest -Recurse -Force

if (Test-Path (Join-Path $dest "SKILL.md")) {
    Write-Host "Installation complete!" -ForegroundColor Green
    Get-ChildItem -Path $dest -Recurse -File | ForEach-Object { Write-Host "  - $($_.FullName)" }
} else {
    Write-Error "Installation failed: SKILL.md not found at destination"
    exit 1
}
