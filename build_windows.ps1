param(
    [switch]$Clean = $true
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host "== SunriseCast Windows Build ==" -ForegroundColor Cyan
Write-Host "Project root: $ProjectRoot"

# Optional: activate venv if it exists
$venvActivate = Join-Path $ProjectRoot "venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    . $venvActivate
} else {
    Write-Host "Virtual environment activation script not found. Continuing with current Python..." -ForegroundColor Yellow
}

# Validate required files
$runFile = Join-Path $ProjectRoot "run.py"
$specFile = Join-Path $ProjectRoot "SunriseCast.spec"

if (-not (Test-Path $runFile)) {
    throw "run.py not found at project root."
}

if (-not (Test-Path $specFile)) {
    throw "SunriseCast.spec not found at project root."
}

# Clean previous outputs
if ($Clean) {
    Write-Host "Cleaning previous build output..." -ForegroundColor Yellow

    $buildDir = Join-Path $ProjectRoot "build"
    $distDir = Join-Path $ProjectRoot "dist"

    if (Test-Path $buildDir) { Remove-Item $buildDir -Recurse -Force }
    if (Test-Path $distDir) { Remove-Item $distDir -Recurse -Force }
}

Write-Host "Checking PyInstaller..." -ForegroundColor Yellow
python -m PyInstaller --version

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller is not available in the current environment."
}

Write-Host "Running PyInstaller with spec file..." -ForegroundColor Yellow
python -m PyInstaller --noconfirm SunriseCast.spec

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

$exePath = Join-Path $ProjectRoot "dist\SunriseCast\SunriseCast.exe"
if (Test-Path $exePath) {
    Write-Host ""
    Write-Host "Build completed successfully." -ForegroundColor Green
    Write-Host "Executable: $exePath" -ForegroundColor Green
} else {
    throw "Build finished, but SunriseCast.exe was not found."
}