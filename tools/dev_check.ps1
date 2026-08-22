[CmdletBinding()]
param(
    [switch]$Quick,
    [switch]$Mutation
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoRoot
$env:UV_PROJECT_ENVIRONMENT = ".venv"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

function Invoke-UvStep {
    param(
        [Parameter(Mandatory)]
        [string]$Label,
        [Parameter(Mandatory)]
        [string[]]$CommandArguments
    )

    Write-Host "==> $Label"
    & uv run @CommandArguments
    if ($LASTEXITCODE -ne 0) { throw "$Label failed with exit code $LASTEXITCODE" }
}

Invoke-UvStep "Compile maintained Python" @("python", "-m", "compileall", "-q", "src", "tools", "tests", "features")
Invoke-UvStep "Ruff format" @("ruff", "format", "--check", ".")
Invoke-UvStep "Ruff lint" @("ruff", "check", ".")
Invoke-UvStep "Strict typing" @("mypy", "src", "tools")
Invoke-UvStep "Architecture dependency contract" @("lint-imports")
Invoke-UvStep "Bounded loop policy" @("python", "-m", "tools.check_loop_policy")

if ($Quick) {
    Invoke-UvStep "Unit and integration tests" @("pytest", "-q")
} else {
    New-Item -ItemType Directory -Path "artifacts" -Force | Out-Null
    Invoke-UvStep "Tests with branch coverage" @(
        "pytest", "-q", "--cov=quality_gate_demo", "--cov-branch",
        "--cov-report=term-missing", "--cov-report=json:artifacts/coverage.json",
        "--junitxml=artifacts/junit.xml"
    )
}

Invoke-UvStep "Gherkin acceptance tests" @("behave", "--no-capture")
Invoke-UvStep "QA command smoke" @("python", "tools/qa_smoke.py")
Invoke-UvStep "Domain cyclomatic complexity" @("xenon", "--max-absolute", "A", "--max-modules", "A", "--max-average", "A", "src")
Invoke-UvStep "Tool cyclomatic complexity" @("xenon", "--max-absolute", "B", "--max-modules", "A", "--max-average", "A", "tools")
Invoke-UvStep "Module size" @("python", "tools/check_module_size.py", "src", "tools", "--max-lines", "200")

if (-not $Quick) {
    Invoke-UvStep "Markdown links" @("python", "tools/check_docs.py")
    Invoke-UvStep "Quantitative summary" @("python", "-m", "tools.write_quality_summary")
    Invoke-UvStep "Dependency audit" @("pip-audit")
    Write-Host "==> Build wheel and source distribution"
    & uv build
    if ($LASTEXITCODE -ne 0) { throw "Package build failed with exit code $LASTEXITCODE" }
}

if ($Mutation) {
    Write-Host "==> Mutation test in WSL"
    & wsl.exe --cd $repoRoot bash -lc "bash tools/mutation_check.sh"
    if ($LASTEXITCODE -ne 0) { throw "Mutation test failed with exit code $LASTEXITCODE" }
}

Write-Host $(if ($Quick) { "QUICK GATE GREEN" } else { "FULL GATE GREEN" })
