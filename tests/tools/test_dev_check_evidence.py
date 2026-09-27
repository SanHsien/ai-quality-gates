from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_powershell_full_gate_invalidates_then_publishes_summary_last() -> None:
    script = (REPO / "tools/dev_check.ps1").read_text(encoding="utf-8")

    invalidate = script.index("Remove-Item -LiteralPath $summaryPath")
    compile_step = script.index('Invoke-UvStep "Compile maintained Python"')
    tests = script.index('Invoke-UvStep "Tests with branch coverage"')
    audit = script.index('Invoke-UvStep "Dependency audit"')
    build = script.index("& uv build")
    stage = script.index('Invoke-UvStep "Stage quantitative summary"')
    publish = script.index("Move-Item -LiteralPath $summaryStagePath")

    assert invalidate < compile_step < tests < audit < build < stage < publish


def test_posix_full_gate_invalidates_then_publishes_summary_last() -> None:
    script = (REPO / "tools/dev_check.sh").read_text(encoding="utf-8")

    invalidate = script.index('rm -f "$summary_path" "$summary_stage_path"')
    compile_step = script.index("uv run python -m compileall")
    tests = script.index("uv run pytest -q --cov=quality_gate_demo")
    audit = script.index("uv run pip-audit")
    build = script.index("uv build")
    stage = script.index("uv run python -m tools.write_quality_summary --output")
    publish = script.index('mv "$summary_stage_path" "$summary_path"')

    assert invalidate < compile_step < tests < audit < build < stage < publish
