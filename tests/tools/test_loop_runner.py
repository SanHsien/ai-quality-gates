from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.loop_runner import check_human_approval_required, main, run_bounded_loop

POLICY_TEMPLATE = """\
version = 1

[loop]
enabled = true
max_iterations = 3
max_parallel_worktrees = 1
max_elapsed_minutes = 30
max_tokens_per_run = 100000
require_isolated_workspace = true
require_independent_verifier = true
persist_state = true
stop_on_repeated_failure = true
repeated_failure_limit = 2
allow_auto_merge = false
allow_direct_main_push = false

[verification]
quick_gate = "python -c 'print(1)'"
full_gate = "python -c 'print(1)'"
require_machine_evidence = true

[state]
path = "{state_path}"
terminal_statuses = [
  "complete",
  "needs_human",
  "budget_exhausted",
  "verification_failed",
]

[connectors]
default_mode = "read-only"
require_explicit_credentials = true

[human_approval]
required_for = [
  "authentication",
  "authorization",
  "payments",
  "personal-data",
  "deletion",
  "deployment",
  "secrets",
  "dependency-major",
]
"""


def _make_policy(
    tmp_path: Path, enabled: bool = True, max_iterations: int = 3
) -> tuple[Path, Path]:
    state_file = tmp_path / "state.json"
    content = POLICY_TEMPLATE.format(state_path=str(state_file).replace("\\", "/"))
    if not enabled:
        content = content.replace("enabled = true", "enabled = false")
    if max_iterations != 3:
        content = content.replace("max_iterations = 3", f"max_iterations = {max_iterations}")
    policy_file = tmp_path / "loop-policy.toml"
    policy_file.write_text(content, encoding="utf-8")
    return policy_file, state_file


def test_human_approval_detection() -> None:
    assert check_human_approval_required("Fix payments calculation") == "payments"
    assert (
        check_human_approval_required("Refactor authentication token handler") == "authentication"
    )
    assert check_human_approval_required("Fix typos in documentation") is None


def test_loop_runner_stops_for_human_approval(tmp_path: Path) -> None:
    policy_path, state_path = _make_policy(tmp_path)
    status, state = run_bounded_loop(
        "Update payments gateway",
        policy_path=policy_path,
    )
    assert status == "needs_human"
    assert state.status == "needs_human"
    assert state_path.is_file()
    saved = json.loads(state_path.read_text(encoding="utf-8"))
    assert saved["status"] == "needs_human"
    assert "payments" in saved["last_failure"]


def test_loop_runner_succeeds_on_first_try(tmp_path: Path) -> None:
    policy_path, state_path = _make_policy(tmp_path)
    status, state = run_bounded_loop(
        "Refactor docstrings",
        policy_path=policy_path,
        verifier=lambda _cmd: (0, "all tests pass"),
        execute_step=lambda _i: ["docs/README.md"],
    )
    assert status == "complete"
    assert state.status == "complete"
    assert state.iteration == 1
    assert state.changed_paths == ["docs/README.md"]
    saved = json.loads(state_path.read_text(encoding="utf-8"))
    assert saved["status"] == "complete"


def test_loop_runner_recovers_on_second_iteration(tmp_path: Path) -> None:
    policy_path, _ = _make_policy(tmp_path)
    calls = 0

    def verifier(_cmd: str) -> tuple[int, str]:
        nonlocal calls
        calls += 1
        return (1, "AssertionError: expected 1 got 2") if calls == 1 else (0, "all tests pass")

    status, state = run_bounded_loop(
        "Fix flaky test",
        policy_path=policy_path,
        verifier=verifier,
        execute_step=lambda i: [f"test_file_{i}.py"],
    )
    assert status == "complete"
    assert state.iteration == 2
    assert state.changed_paths == ["test_file_1.py", "test_file_2.py"]


def test_loop_runner_stops_on_repeated_failure(tmp_path: Path) -> None:
    policy_path, state_path = _make_policy(tmp_path)
    status, state = run_bounded_loop(
        "Fix broken parser",
        policy_path=policy_path,
        verifier=lambda _cmd: (1, "SyntaxError: invalid token"),
    )
    assert status == "verification_failed"
    assert state.status == "verification_failed"
    assert state.next_action == "stop_repeated_failure"


def test_loop_runner_stops_on_iteration_limit(tmp_path: Path) -> None:
    policy_path, _ = _make_policy(tmp_path, max_iterations=2)
    step = 0

    def verifier(_cmd: str) -> tuple[int, str]:
        nonlocal step
        step += 1
        return (1, f"Error iteration {step}")

    status, state = run_bounded_loop(
        "Complex migration",
        policy_path=policy_path,
        verifier=verifier,
    )
    assert status == "budget_exhausted"
    assert state.status == "budget_exhausted"


def test_loop_runner_refuses_disabled_policy(tmp_path: Path) -> None:
    policy_path, _ = _make_policy(tmp_path, enabled=False)
    with pytest.raises(ValueError, match="disabled by policy"):
        run_bounded_loop(
            "Task with disabled policy",
            policy_path=policy_path,
            allow_disabled=False,
        )


def test_cli_main_exit_codes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    policy_path, _ = _make_policy(tmp_path)
    monkeypatch.setattr("tools.loop_runner._default_verifier", lambda _cmd: (0, "pass"))
    exit_code = main(["--task", "Clean code", "--policy", str(policy_path)])
    assert exit_code == 0

    exit_needs_human = main(["--task", "Delete secrets", "--policy", str(policy_path)])
    assert exit_needs_human == 2
