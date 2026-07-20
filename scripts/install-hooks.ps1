# Install git pre-push hook that runs scripts/verify.ps1 (same path as CI).
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $RepoRoot
try {
    $null = git rev-parse --is-inside-work-tree 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Not a git repository: $RepoRoot"
    }

    $GitDir = (git rev-parse --git-dir).Trim()
    if (-not [System.IO.Path]::IsPathRooted($GitDir)) {
        $GitDir = Join-Path $RepoRoot $GitDir
    }

    $HooksDir = Join-Path $GitDir "hooks"
    New-Item -ItemType Directory -Force -Path $HooksDir | Out-Null

    $Target = Join-Path $HooksDir "pre-push"
    $HookBody = @'
#!/bin/sh
# Installed by scripts/install-hooks.ps1 — runs CI verify before push.
REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT" || exit 1
if command -v pwsh >/dev/null 2>&1; then
  exec pwsh -NoProfile -File scripts/verify.ps1
fi
if command -v powershell >/dev/null 2>&1; then
  exec powershell -NoProfile -File scripts/verify.ps1
fi
if [ -f scripts/verify.sh ]; then
  exec bash scripts/verify.sh
fi
echo "pre-push: no verify runner found" >&2
exit 1
'@
    # UTF-8 without BOM for git-for-windows sh.
    [System.IO.File]::WriteAllText($Target, $HookBody.Replace("`r`n", "`n"))

    Write-Host "Installed pre-push hook -> $Target"
    Write-Host "Push will now run scripts/verify.ps1 (compileall + selftest + pytest + pyright)."
}
finally {
    Pop-Location
}
