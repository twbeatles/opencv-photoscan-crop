# Photo Cropper — 통합 검증 스크립트 (PowerShell)
# Python exit code만 신뢰합니다 (stderr 로그로 인한 false negative 방지).

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

function Resolve-AppDir {
    param([string]$Root)
    foreach ($name in @("opencv", ";opencv")) {
        $candidate = Join-Path $Root $name
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }
    throw "App directory not found (expected opencv/ or ;opencv/ under $Root)"
}

$AppDir = Resolve-AppDir -Root $RepoRoot
Write-Host "==> App directory: $AppDir"

$env:PYTHONUTF8 = "1"
$env:QT_QPA_PLATFORM = "offscreen"
$env:PHOTOCROPPER_OFFLINE = "1"

Push-Location -LiteralPath $AppDir
try {
    Write-Host "==> compileall"
    python -m compileall -q photo_cropper
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "==> selftest"
    python -m photo_cropper.selftest
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "==> pytest (unit)"
    python -m pytest tests/test_path_validation.py -q
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "==> pyright"
    $PyrightConfig = Join-Path $RepoRoot "pyrightconfig.json"
    if (-not (Test-Path -LiteralPath $PyrightConfig)) {
        $PyrightConfig = Join-Path $AppDir "pyrightconfig.json"
    }
    pyright --project $PyrightConfig
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "VERIFY OK"
    exit 0
}
finally {
    Pop-Location
}