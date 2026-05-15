# ============================================================================
# Repo reorganization — root cleanup
# ----------------------------------------------------------------------------
# Run this from the repo root. It is idempotent: safe to re-run.
# Each operation is gated on existence/tracking checks, and uses `git mv` /
# `git rm` when the path is tracked (to preserve history) or PowerShell's
# Move-Item / Remove-Item when it isn't.
#
#   cd f:\tech-projects\yt-dlp-studio-project\yt-dlp-studio
#   .\scripts\reorganize.ps1
#
# Review the changes, then commit per the suggested groupings at the bottom of
# the output.
# ============================================================================

$ErrorActionPreference = "Stop"
Set-Location -Path (Join-Path $PSScriptRoot '..')

function Test-GitTracked {
    param([string]$Path)
    $null = git ls-files --error-unmatch -- $Path 2>$null
    return ($LASTEXITCODE -eq 0)
}

function Move-Tracked {
    param([string]$From, [string]$To)
    if (-not (Test-Path $From)) {
        Write-Host "  skip (not present): $From" -ForegroundColor DarkGray
        return
    }
    $destDir = Split-Path -Parent $To
    if ($destDir -and -not (Test-Path $destDir)) {
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    }
    if (Test-GitTracked $From) {
        Write-Host "  git mv $From -> $To" -ForegroundColor Cyan
        git mv -- $From $To
    } else {
        Write-Host "  mv (untracked) $From -> $To" -ForegroundColor Yellow
        Move-Item -Path $From -Destination $To -Force
    }
}

function Remove-Tracked {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        Write-Host "  skip (not present): $Path" -ForegroundColor DarkGray
        return
    }
    if (Test-GitTracked $Path) {
        Write-Host "  git rm $Path" -ForegroundColor Magenta
        git rm -rf -- $Path | Out-Null
    } else {
        Write-Host "  rm (untracked) $Path" -ForegroundColor Yellow
        Remove-Item -Path $Path -Recurse -Force
    }
}

# ----------------------------------------------------------------------------
# 1. Create target directories
# ----------------------------------------------------------------------------
Write-Host "`n[1/6] Creating target directories" -ForegroundColor Green
foreach ($d in @('packaging', 'vendor', 'requirements', 'docs-internal')) {
    if (-not (Test-Path $d)) {
        New-Item -ItemType Directory -Path $d | Out-Null
        Write-Host "  created $d/" -ForegroundColor Cyan
    } else {
        Write-Host "  exists  $d/" -ForegroundColor DarkGray
    }
}

# ----------------------------------------------------------------------------
# 2. Move PyInstaller files into packaging/
# ----------------------------------------------------------------------------
Write-Host "`n[2/6] Moving PyInstaller files -> packaging/" -ForegroundColor Green
Move-Tracked 'build.spec'       'packaging/build.spec'
Move-Tracked 'build_linux.spec' 'packaging/build_linux.spec'
Move-Tracked 'hook-yt_dlp.py'   'packaging/hook-yt_dlp.py'
Move-Tracked 'version_info.txt' 'packaging/version_info.txt'

# ----------------------------------------------------------------------------
# 3. Vendor and internal docs
# ----------------------------------------------------------------------------
Write-Host "`n[3/6] Moving vendored code and internal docs" -ForegroundColor Green
Move-Tracked 'yt_dlp_engine'         'vendor/yt_dlp_engine'
Move-Tracked 'open-source-templates' 'docs-internal/templates'

# ----------------------------------------------------------------------------
# 4. Requirements consolidation
# ----------------------------------------------------------------------------
# pyproject.toml is now the single source of truth for dependency declarations
# (see [project.dependencies] and [project.optional-dependencies]).
# requirements.txt and requirements-dev.txt were duplicating those — removed.
# requirements.lock keeps its hash-pinned values; regenerate next time with:
#   pip-compile --generate-hashes -o requirements/lock.txt pyproject.toml
# ----------------------------------------------------------------------------
Write-Host "`n[4/6] Consolidating requirements" -ForegroundColor Green
Move-Tracked 'requirements.lock' 'requirements/lock.txt'
Remove-Tracked 'requirements.txt'
Remove-Tracked 'requirements-dev.txt'

# ----------------------------------------------------------------------------
# 5. Deletions and renames of stale files
# ----------------------------------------------------------------------------
Write-Host "`n[5/6] Deleting stale files" -ForegroundColor Green
# RELEASE_NOTES.md duplicates the v0.9.2 CHANGELOG entry; the install/system-
# requirements prose belongs in README, not in a release file.
Remove-Tracked 'RELEASE_NOTES.md'
# Replaced by docs-internal/deno-pinning-reference.md (already created).
Remove-Tracked 'deno.sha256sum'
# Replaced by scripts/check_imports.py (already created), which uses the new
# vendor/yt_dlp_engine path and avoids pytest auto-collection.
Remove-Tracked 'test_imports.py'
# Broken hardcoded absolute path; verifies v2.1.0 fields that have shipped.
Remove-Tracked 'test_new_fields.py'
# Build artifact (also matched by *.log in .gitignore).
Remove-Tracked 'build_output.log'

# ----------------------------------------------------------------------------
# 6. Done
# ----------------------------------------------------------------------------
Write-Host "`n[6/6] Done." -ForegroundColor Green
Write-Host @"

Next steps:
  1. Review changes:
       git status
       git diff --stat
  2. Build the EXE locally to confirm PyInstaller still works:
       pyinstaller packaging/build.spec
  3. Commit in groups (suggested):
       a) chore(repo): move PyInstaller files to packaging/
       b) chore(repo): vendor yt_dlp_engine under vendor/
       c) chore(repo): consolidate requirements; rely on pyproject.toml
       d) chore(repo): drop stale files (RELEASE_NOTES, ad-hoc test scripts, etc.)
       e) docs(internal): move open-source-templates to docs-internal/

If git mv resulted in a (rename) you can verify with:
  git log --follow --stat -- packaging/build.spec
"@ -ForegroundColor White
