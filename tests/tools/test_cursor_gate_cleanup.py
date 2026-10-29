"""Timeout cleanup stays bounded even when a surviving descendant owns the pipes."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock

import pytest

from tools import cursor_gate_core as core


@pytest.mark.parametrize("partial", [None, b"partial\xff\n"])
def test_cleanup_timeout_returns_124_with_available_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, partial: bytes | None
) -> None:
    proc = Mock()
    proc.communicate.side_effect = [
        subprocess.TimeoutExpired("gate", 2),
        subprocess.TimeoutExpired("gate", 1, output=partial, stderr=b"diagnostic\n"),
    ]
    monkeypatch.setattr(core.subprocess, "Popen", Mock(return_value=proc))
    kill = Mock()
    monkeypatch.setattr(core, "_kill_tree", kill)

    result = core.run_gate(tmp_path, core.GateSpec("gate", "test", 2))

    assert result.exit_code == 124
    assert result.status == "failed"
    assert "diagnostic" in result.output
    assert "gate timed out" in result.output
    if partial:
        assert "partial\ufffd" in result.output
    kill.assert_called_once_with(proc)
    assert proc.communicate.call_args.kwargs["timeout"] == 1


def test_surviving_grandchild_does_not_extend_cleanup_indefinitely(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pid_file = tmp_path / "grandchild.pid"
    script = tmp_path / "gate.py"
    script.write_text(
        "import subprocess, sys, time\n"
        "from pathlib import Path\n"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
        f"Path({str(pid_file)!r}).write_text(str(child.pid))\n"
        "time.sleep(30)\n",
        encoding="utf-8",
    )
    popen = subprocess.Popen

    def start_gate(_command: str, **kwargs: object) -> subprocess.Popen[bytes]:
        # Bypass the shell so killing the direct child leaves only the grandchild alive.
        kwargs["shell"] = False
        return popen([sys.executable, str(script)], **kwargs)

    monkeypatch.setattr(core.subprocess, "Popen", start_gate)
    monkeypatch.setattr(core, "_kill_tree", lambda proc: proc.kill())
    with ThreadPoolExecutor(max_workers=1) as pool:
        started = time.monotonic()
        future = pool.submit(core.run_gate, tmp_path, core.GateSpec("gate", "test", 2))
        try:
            result = future.result(timeout=5)
            assert time.monotonic() - started < 5  # 2s gate + 1s grace + scheduling margin
            assert result.exit_code == 124
            assert "gate timed out" in result.output
            assert pid_file.exists(), "grandchild must start and inherit the pipes"
        finally:
            if pid_file.exists():
                os.kill(int(pid_file.read_text()), signal.SIGTERM)
