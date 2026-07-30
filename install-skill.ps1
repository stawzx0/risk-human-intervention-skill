<#
.SYNOPSIS
    Install risk-human-intervention skill into Codex CLI skills directory.
.DESCRIPTION
    Copies the risk-human-intervention skill from the source directory
    to the Codex skills directory for automatic registration.
.EXAMPLE
    .\install-skill.ps1
#>

$source = Join-Path $PSScriptRoot "risk-human-skill"
$dest = Join-Path $env:USERPROFILE ".codex\skills\risk-human-intervention"

if (-not (Test-Path $source)) {
    # Try relative to script dir
    $source = Join-Path (Split-Path $PSScriptRoot -Parent) "risk-human-skill"
}

if (-not (Test-Path $source)) {
    Write-Error "Source skill directory not found. Expected at: $source"
    exit 1
}

Write-Host "Installing risk-human-intervention skill..." -ForegroundColor Cyan
Write-Host "  From: $source"
Write-Host "  To:   $dest"

# Create destination
New-Item -ItemType Directory -Path $dest -Force | Out-Null

# Copy files
Copy-Item -Path "$source\*" -Destination $dest -Recurse -Force

# Verify
if (Test-Path (Join-Path $dest "SKILL.md")) {
    Write-Host "Installation complete!" -ForegroundColor Green
    Write-Host "Files installed:" -ForegroundColor Green
    Get-ChildItem -Path $dest -Recurse -File | ForEach-Object { Write-Host "  - $($_.Name)" }
} else {
    Write-Error "Installation failed: SKILL.md not found at destination"
    exit 1
}
