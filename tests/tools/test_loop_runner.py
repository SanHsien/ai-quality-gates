from __future__ import annotations

import json
import sys
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
        verifier=lambda _cmd, timeout=None: (0, "all tests pass"),
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

    def verifier(_cmd: str, timeout: float | None = None) -> tuple[int, str]:
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
        verifier=lambda _cmd, timeout=None: (1, "SyntaxError: invalid token"),
    )
    assert status == "verification_failed"
    assert state.status == "verification_failed"
    assert state.next_action == "stop_repeated_failure"


def test_loop_runner_stops_on_iteration_limit(tmp_path: Path) -> None:
    policy_path, _ = _make_policy(tmp_path, max_iterations=2)
    step = 0

    def verifier(_cmd: str, timeout: float | None = None) -> tuple[int, str]:
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
    monkeypatch.setattr(
        "tools.loop_runner._default_verifier", lambda _cmd, timeout=None: (0, "pass")
    )
    exit_code = main(["--task", "Clean code", "--policy", str(policy_path)])
    assert exit_code == 0

    exit_needs_human = main(["--task", "Delete secrets", "--policy", str(policy_path)])
    assert exit_needs_human == 2


def test_loop_runner_stops_on_repeated_failure_with_varying_time(tmp_path: Path) -> None:
    policy_path, state_path = _make_policy(tmp_path, max_iterations=3)
    fail_line = "FAILED tests/test_a.py::test_fn - AssertionError: 1 != 2"
    outputs = [
        f"{fail_line}\n========================= 1 failed in 0.52s =========================",
        f"{fail_line}\n========================= 1 failed in 0.48s =========================",
    ]
    calls = 0

    def verifier(_cmd: str, timeout: float | None = None) -> tuple[int, str]:
        nonlocal calls
        out = outputs[calls]
        calls += 1
        return 1, out

    status, state = run_bounded_loop(
        "Fix flake",
        policy_path=policy_path,
        verifier=verifier,
    )
    assert status == "verification_failed"
    assert state.status == "verification_failed"
    assert state.next_action == "stop_repeated_failure"
    assert calls == 2


def test_loop_runner_terminates_verifier_when_budget_exhausted(tmp_path: Path) -> None:
    policy_path, _ = _make_policy(tmp_path)
    import subprocess

    def timeout_verifier(cmd: str, timeout: float | None = None) -> tuple[int, str]:
        raise subprocess.TimeoutExpired(cmd, timeout or 1.0)

    status, state = run_bounded_loop(
        "Long verification",
        policy_path=policy_path,
        verifier=timeout_verifier,
    )
    assert status == "budget_exhausted"
    assert state.status == "budget_exhausted"
    assert state.next_action == "stop_time_limit"


def test_default_verifier_times_out() -> None:
    import subprocess

    from tools.loop_runner import _default_verifier

    with pytest.raises(subprocess.TimeoutExpired):
        _default_verifier('python -c "import time; time.sleep(2)"', timeout=0.05)


def test_loop_runner_stops_on_repeated_failure_summary_only_varying_time(tmp_path: Path) -> None:
    policy_path, _ = _make_policy(tmp_path, max_iterations=3)
    outputs = [
        "========================= 1 failed in 0.52s =========================",
        "========================= 1 failed in 0.48s =========================",
    ]
    calls = 0

    def verifier(_cmd: str, timeout: float | None = None) -> tuple[int, str]:
        nonlocal calls
        out = outputs[calls]
        calls += 1
        return 1, out

    status, state = run_bounded_loop("Summary only", policy_path=policy_path, verifier=verifier)
    assert status == "verification_failed"
    assert state.next_action == "stop_repeated_failure"
    assert calls == 2


def test_loop_runner_resets_failure_count_on_different_failure(tmp_path: Path) -> None:
    policy_path, _ = _make_policy(tmp_path, max_iterations=3)
    fail_a = "FAILED tests/test_a.py::test_one - AssertionError: 1 != 2"
    fail_b = "FAILED tests/test_b.py::test_two - AssertionError: 2 != 3"
    sep = "=" * 25
    outputs = [
        f"{fail_a}\n{sep} 1 failed in 0.52s {sep}",
        f"{fail_b}\n{sep} 1 failed in 0.48s {sep}",
        f"{sep} 1 passed in 0.10s {sep}",
    ]
    calls = 0

    def verifier(_cmd: str, timeout: float | None = None) -> tuple[int, str]:
        nonlocal calls
        out = outputs[calls]
        calls += 1
        return (0 if "passed" in out else 1), out

    status, state = run_bounded_loop("Different errors", policy_path=policy_path, verifier=verifier)
    assert status == "complete"
    assert calls == 3


def test_default_verifier_timeout_kills_the_whole_process_tree(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import subprocess
    import time

    from tools.loop_runner import _default_verifier

    grandchild = "import time; time.sleep(30)"
    parent = (
        "import subprocess, sys, time; "
        f"subprocess.Popen([sys.executable, '-c', {grandchild!r}]); time.sleep(30)"
    )
    command = f'"{sys.executable}" -c "{parent}"'
    # A long reap window: only a real tree kill (not just killing the shell)
    # releases the pipes the grandchild holds before it expires.
    monkeypatch.setattr("tools.loop_verifier._REAP_SECONDS", 60)

    started = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        _default_verifier(command, timeout=0.5)
    assert time.monotonic() - started < 10


def test_default_verifier_returns_even_if_tree_kill_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import subprocess
    import time

    from tools.loop_runner import _default_verifier

    monkeypatch.setattr("tools.loop_verifier._kill_tree", lambda proc: proc.kill())
    monkeypatch.setattr("tools.loop_verifier._REAP_SECONDS", 1)
    grandchild_life = 5
    grandchild = f"import time; time.sleep({grandchild_life})"
    parent = (
        "import subprocess, sys, time; "
        f"subprocess.Popen([sys.executable, '-c', {grandchild!r}]); time.sleep(30)"
    )
    command = f'"{sys.executable}" -c "{parent}"'

    started = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        _default_verifier(command, timeout=0.5)
    assert time.monotonic() - started < grandchild_life - 1


def test_kill_tree_survives_taskkill_being_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    from tools import loop_verifier

    def no_taskkill(*_args: object, **_kwargs: object) -> None:
        raise FileNotFoundError("taskkill")

    killed: list[bool] = []

    class FakeProc:
        pid = 0

        def kill(self) -> None:
            killed.append(True)

    monkeypatch.setattr(loop_verifier.sys, "platform", "win32")
    monkeypatch.setattr(loop_verifier.subprocess, "run", no_taskkill)
    loop_verifier._kill_tree(FakeProc())  # type: ignore[arg-type]
    assert killed == [True]


def test_default_verifier_failure_output_keeps_stdout_and_stderr() -> None:

    from tools.loop_runner import _default_verifier

    child = (
        "import sys; print('FAILED tests/test_a.py::test_x'); "
        "print('wrapper threw', file=sys.stderr); sys.exit(1)"
    )
    code, output = _default_verifier(f'"{sys.executable}" -c "{child}"')
    assert code == 1
    assert "FAILED tests/test_a.py::test_x" in output
    assert "wrapper threw" in output


@pytest.mark.parametrize(
    ("first", "second", "same"),
    [
        ("Ran 1 test\nTook 0min 0.002s", "Ran 1 test\nTook 0min 0.004s", True),
        ("1 failed in 63.12s (0:01:03)", "1 failed in 61.80s (0:01:01)", True),
        ("Found 2 errors in 5 files", "Found 2 errors in 3 files", False),
        (
            "FAILED tests/a.py::t - AssertionError: 1 != 2",
            "FAILED tests/a.py::t - AssertionError: 7 != 8",
            True,
        ),
        ("ERROR tests/a.py::t - boom", "ERROR tests/b.py::t - boom", False),
        ("FAILED tests/a.py::t - x", "FAILED tests/b.py::t - x", False),
        ("SyntaxError: Unexpected token (12:34)", "SyntaxError: Unexpected token (56:78)", False),
        ("expected -1", "expected 1", False),
        ("FAILED tests/a.py::t[x - y] - m", "FAILED tests/a.py::t[x - z] - m", False),
    ],
)
def test_failure_signature_equality(first: str, second: str, same: bool) -> None:
    from tools.loop_signature import failure_signature

    assert (failure_signature(first, 1) == failure_signature(second, 1)) is same


def test_failure_signature_never_falls_back_to_the_raw_line_when_only_timing() -> None:
    from tools.loop_signature import failure_signature

    assert failure_signature("Took 0min 0.002s", 3) == "exit 3"
