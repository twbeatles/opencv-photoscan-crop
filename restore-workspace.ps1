# Cursor/에디터를 닫은 뒤 관리자 PowerShell에서 실행하세요.
# 손상된 opencv-photoscan-crop 폴더를 백업하고 recovery 클론으로 교체합니다.

$ErrorActionPreference = 'Stop'
$repos = 'D:\twbeatles-repos'
$broken = Join-Path $repos 'opencv-photoscan-crop'
$recovery = Join-Path $repos 'opencv-photoscan-crop-recovery'
$backup = Join-Path $repos ('opencv-photoscan-crop.broken-{0:yyyyMMdd-HHmmss}' -f (Get-Date))

if (-not (Test-Path $recovery)) {
    throw "Recovery clone not found: $recovery"
}

if (Test-Path $recovery) {
    if (Test-Path $broken) {
        try {
            Write-Host "Backing up broken workspace -> $backup"
            Rename-Item -LiteralPath $broken -NewName (Split-Path $backup -Leaf)
            Write-Host "Promoting recovery clone -> $broken"
            Rename-Item -LiteralPath $recovery -NewName 'opencv-photoscan-crop'
        }
        catch {
            Write-Host "Rename blocked (editor lock). Mirroring recovery into existing workspace instead..."
            robocopy $recovery $broken /MIR /XD .git mcps terminals .codegraph backups .vscode /R:1 /W:1 | Out-Null
            if ($LASTEXITCODE -ge 8) { throw "robocopy failed with exit code $LASTEXITCODE" }
        }
    }
    else {
        Rename-Item -LiteralPath $recovery -NewName 'opencv-photoscan-crop'
    }
}

Write-Host 'Done. Workspace root: D:\twbeatles-repos\opencv-photoscan-crop'