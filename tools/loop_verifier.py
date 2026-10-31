"""Run a loop verification command and really stop it when it times out."""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys
import time
from collections.abc import Callable

_REAP_SECONDS = 5


def _kill_tree(proc: subprocess.Popen[str]) -> None:
    """Kill the shell and everything it started (`shell=True` alone kills only the shell)."""
    if sys.platform == "win32":
        with contextlib.suppress(OSError, subprocess.SubprocessError):
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
                check=False,
                timeout=_REAP_SECONDS,
            )
    else:  # pragma: no cover - exercised on POSIX CI only
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)
    proc.kill()


def run_verifier(command: str, timeout: float | None = None) -> tuple[int, str]:
    """Return (exit code, output). On timeout the whole process tree is killed, then re-raised.

    On failure the output is stdout followed by stderr: test runners print the
    FAILED lines to stdout while wrappers such as dev_check.ps1 throw to stderr,
    and the repeated-failure check needs the former.
    """
    group: dict[str, object] = (
        {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
        if sys.platform == "win32"
        else {"start_new_session": True}
    )
    proc = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        **group,  # type: ignore[call-overload]
    )
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.communicate(timeout=_REAP_SECONDS)
        raise
    return proc.returncode, out if proc.returncode == 0 else "\n".join(x for x in (out, err) if x)


def run_within_budget(
    runner: Callable[..., tuple[int, str]],
    command: str,
    start_time: float,
    max_elapsed_minutes: int,
) -> tuple[int, str] | None:
    """Run ``runner`` with the remaining time budget; ``None`` means the budget ran out."""
    remaining = (max_elapsed_minutes * 60.0) - (time.monotonic() - start_time)
    if remaining <= 0:
        return None
    try:
        result = runner(command, timeout=remaining)
        return None if (time.monotonic() - start_time) / 60.0 > max_elapsed_minutes else result
    except (subprocess.TimeoutExpired, TimeoutError):
        return None
