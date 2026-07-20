# Optional benchmark gate: exits 0 when labels/images are not present.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$opencv = Join-Path $root "opencv"
$labels = Join-Path $opencv "benchmark\labels.json"
$images = Join-Path $opencv "benchmark\images"

if (-not (Test-Path $labels)) {
    Write-Host "SKIP benchmark: opencv/benchmark/labels.json not found"
    exit 0
}
if (-not (Test-Path $images)) {
    Write-Host "SKIP benchmark: opencv/benchmark/images not found"
    exit 0
}

Push-Location $opencv
try {
    python -m photo_cropper.benchmark `
        --images .\benchmark\images `
        --labels .\benchmark\labels.json `
        --report .\benchmark\report.json `
        --detect-mode accurate
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
