<#
.SYNOPSIS
    Build Lei_MD Windows executable (and optional NSIS installer) from source.

.DESCRIPTION
    One-shot Windows build. Reads the version from pyproject.toml (single
    source of truth) and produces dist/Lei_MD-<version>.exe. Handles:
      - Reading the version from pyproject.toml
      - Creating an isolated build venv
      - Installing project + dev + build deps
      - Running PyInstaller against Lei_MD.spec
      - (optional) Running NSIS to wrap into Lei_MD-<version>-Setup.exe
      - Copying artifacts to ./dist/ for upload

.PARAMETER WithInstaller
    Also build the NSIS installer (requires NSIS on $PATH or in $env:ProgramFiles).

.PARAMETER SkipVenv
    Use the system Python instead of an isolated venv (faster, but risks dep conflicts).

.EXAMPLE
    pwsh scripts/build-windows.ps1
    # Builds dist/Lei_MD-<version>.exe (onefile), where <version> is read
    # from pyproject.toml.

.EXAMPLE
    pwsh scripts/build-windows.ps1 -WithInstaller
    # Also builds installer/Lei_MD-<version>-Setup.exe

.NOTES
    Run on Windows 11 with Python 3.10-3.13 and PyInstaller 6.x.
    See docs/07-build-release.md for prerequisites and troubleshooting.
#>

[CmdletBinding()]
param(
    [switch]$WithInstaller,
    [switch]$SkipVenv,
    [switch]$Clean
)

$ErrorActionPreference = 'Stop'
$ProgressPreference    = 'Continue'

# ──────────────────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────────────────
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$SpecFile    = Join-Path $ProjectRoot 'Lei_MD.spec'
$DistDir     = Join-Path $ProjectRoot 'dist'
$BuildDir    = Join-Path $ProjectRoot 'build'
$InstallerDir = Join-Path $ProjectRoot 'installer'
$InstallerScript = Join-Path $InstallerDir 'installer.nsi'
$VenvDir     = Join-Path $ProjectRoot '.venv-build'

$AppName    = 'Lei_MD'

# Single source of truth: read version from pyproject.toml.
# `python -c "..."` is the most portable cross-platform reader we have
# (works on Windows + Linux + macOS), and it avoids depending on extra
# PowerShell modules like powershell-yaml or tomllib-from-PS7-only.
$AppVersion = (& python -c "import tomllib, sys; print(tomllib.load(open(sys.argv[1],'rb'))['project']['version'])" (Join-Path $ProjectRoot 'pyproject.toml')).Trim()
if (-not ($AppVersion -match '^\d+\.\d+\.\d+([.-].+)?$')) {
    throw "Could not parse a semver-like version from pyproject.toml: '$AppVersion'"
}
$ExeName    = "$AppName-$AppVersion.exe"

# ──────────────────────────────────────────────────────────────────────
# Sanity checks
# ──────────────────────────────────────────────────────────────────────
Write-Host "==> Lei_MD build script v$AppVersion" -ForegroundColor Cyan
Write-Host "    ProjectRoot: $ProjectRoot"
Write-Host "    Spec:        $SpecFile"

if (-not (Test-Path $SpecFile)) {
    throw "Lei_MD.spec not found at $SpecFile. Are you in the right repo?"
}

# Python check
$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) {
    throw "python not found on PATH. Install Python 3.10-3.13 first."
}
$pyVer = & python --version 2>&1
Write-Host "    Python:     $pyVer"

# ──────────────────────────────────────────────────────────────────────
# Optional clean
# ──────────────────────────────────────────────────────────────────────
if ($Clean) {
    Write-Host "==> Clean: removing build/ dist/ and venv" -ForegroundColor Yellow
    if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir }
    if (Test-Path $DistDir)  { Remove-Item -Recurse -Force $DistDir  }
    if (Test-Path $VenvDir)  { Remove-Item -Recurse -Force $VenvDir  }
}

# ──────────────────────────────────────────────────────────────────────
# Build venv
# ──────────────────────────────────────────────────────────────────────
$venvPython = $python
if (-not $SkipVenv) {
    if (-not (Test-Path $VenvDir)) {
        Write-Host "==> Creating build venv at $VenvDir" -ForegroundColor Cyan
        & python -m venv $VenvDir
    }
    $venvPython = Join-Path $VenvDir 'Scripts\python.exe'
    Write-Host "    Venv:       $venvPython"

    Write-Host "==> Installing project + build deps" -ForegroundColor Cyan
    & $venvPython -m pip install --upgrade pip --quiet
    & $venvPython -m pip install -e "$ProjectRoot[dev]" --quiet
    & $venvPython -m pip install pyinstaller --quiet
}

# Verify pyinstaller is available
$pyinstaller = & $venvPython -m PyInstaller --version 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller not available. Run without -SkipVenv or install manually: pip install pyinstaller"
}
Write-Host "    PyInstaller: $pyinstaller"

# ──────────────────────────────────────────────────────────────────────
# Run PyInstaller
# ──────────────────────────────────────────────────────────────────────
Write-Host "==> Running PyInstaller (this takes 1-3 minutes)..." -ForegroundColor Cyan
Push-Location $ProjectRoot
try {
    & $venvPython -m PyInstaller --noconfirm $SpecFile
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}

$builtExe = Join-Path $DistDir $ExeName
if (-not (Test-Path $builtExe)) {
    throw "Expected $builtExe but it wasn't created. Check PyInstaller output above."
}
$size = (Get-Item $builtExe).Length / 1MB
Write-Host "    Built:      $builtExe  ($([math]::Round($size, 1)) MB)" -ForegroundColor Green

# ──────────────────────────────────────────────────────────────────────
# Optional NSIS installer
# ──────────────────────────────────────────────────────────────────────
if ($WithInstaller) {
    Write-Host "==> Building NSIS installer..." -ForegroundColor Cyan
    $makensis = (Get-Command makensis -ErrorAction SilentlyContinue).Source
    if (-not $makensis) {
        $candidates = @(
            "$env:ProgramFiles (x86)\NSIS\makensis.exe",
            "$env:ProgramFiles\NSIS\makensis.exe"
        )
        $makensis = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    }
    if (-not $makensis) {
        Write-Warning "NSIS (makensis.exe) not found on PATH or in Program Files."
        Write-Warning "Download from https://nsis.sourceforge.io/Download and re-run with -WithInstaller."
    } else {
        Write-Host "    NSIS:       $makensis"
        Push-Location $InstallerDir
        try {
            & $makensis /DAPP_VERSION="$AppVersion" $InstallerScript
            if ($LASTEXITCODE -ne 0) { throw "makensis failed" }
        } finally {
            Pop-Location
        }
        $setupExe = Join-Path $InstallerDir "Lei_MD-$AppVersion-Setup.exe"
        if (Test-Path $setupExe) {
            $setupSize = (Get-Item $setupExe).Length / 1MB
            Write-Host "    Installer:  $setupExe  ($([math]::Round($setupSize, 1)) MB)" -ForegroundColor Green
        }
    }
}

# ──────────────────────────────────────────────────────────────────────
# Summary
# ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "==> Build complete!" -ForegroundColor Green
Write-Host ""
Write-Host "    Executable:   $builtExe" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Smoke test the exe (double-click or run in cmd):"
Write-Host "       $builtExe --help   # should not error"
Write-Host ""
Write-Host "  2. Upload to GitHub Release v${AppVersion}:"
Write-Host "       https://github.com/raymondyan-zhijie/Lei_MD/releases/tag/v${AppVersion}"
Write-Host "     (drag-and-drop the .exe in the browser, or use `gh release upload`)"
Write-Host ""
if ($WithInstaller) {
    Write-Host "  3. Upload the NSIS installer too:"
    Write-Host "       installer/Lei_MD-$AppVersion-Setup.exe" -ForegroundColor Cyan
}
