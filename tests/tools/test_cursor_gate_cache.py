"""Cache policy: timeouts remain evidence but must never suppress a retry."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tools import cursor_gate_router as router


@pytest.mark.parametrize("exit_code", [0, 1, 124])
def test_evaluate_retries_only_timeout_for_unchanged_fingerprint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, exit_code: int
) -> None:
    state_file = tmp_path / "state.json"
    spec = router.GateSpec("echo gate", "test")
    initial = router.GateResult(
        "passed" if exit_code == 0 else "failed", spec.command, spec.source, exit_code, "first"
    )
    recovered = router.GateResult("passed", spec.command, spec.source, 0, "recovered")
    runner = Mock(side_effect=[initial, initial, recovered])
    monkeypatch.setattr(router, "_state_path", lambda: state_file)
    monkeypatch.setattr(router, "effective_gate", lambda _repo: spec)
    monkeypatch.setattr(router, "git_state", lambda _repo: "unchanged")
    monkeypatch.setattr(router, "run_gate", runner)

    assert router.evaluate(tmp_path) == initial
    first = next(iter(json.loads(state_file.read_text(encoding="utf-8")).values()))
    assert first["exit_code"] == exit_code
    assert first["output"] == "first"
    assert router.evaluate(tmp_path) == initial
    if exit_code == 124:
        assert runner.call_count == 2
        assert router.evaluate(tmp_path) == recovered
        assert router.evaluate(tmp_path) == recovered
        assert runner.call_count == 3
        final = next(iter(json.loads(state_file.read_text(encoding="utf-8")).values()))
        assert final["fingerprint"] == first["fingerprint"]
        assert final["exit_code"] == 0
    else:
        assert runner.call_count == 1
