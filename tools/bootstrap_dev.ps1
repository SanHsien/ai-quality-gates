[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoRoot
$env:UV_PROJECT_ENVIRONMENT = ".venv"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

uv sync --frozen --python 3.12
if ($LASTEXITCODE -ne 0) { throw "uv sync failed" }

Write-Host "BOOTSTRAP GREEN: run pwsh -NoProfile -File tools\dev_check.ps1 -Quick"
