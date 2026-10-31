"""Stable failure signature so "same failure twice" ignores timings."""

from __future__ import annotations

import re

_ANSI = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
# A duration needs a unit: "in 0.52s" / "Took 0min" are timings, "in 5 files" is not.
_TIMING = re.compile(r"\b(?:in|took)\s+\d+(?:\.\d+)?(?:min|ms|m|s)\b", re.I)
_BARE_DURATION = re.compile(r"\b\d+(?:\.\d+)?(?:min|ms|s)\b", re.I)
_CLOCK = re.compile(r"\(\d+:\d{2}:\d{2}\)")  # pytest's "(0:01:03)"; "(12:34)" is line:column


def _test_id(line: str) -> str:
    """The test id of a FAILED/ERROR line: everything before the ` - message` part."""
    head, sep, _ = line.partition("] - ")
    return re.sub(r"\s+", " ", head + "]" if sep else line.split(" - ", 1)[0])


def _failed_ids(lines: list[str]) -> list[str]:
    return sorted(_test_id(line) for line in lines if line.startswith(("FAILED ", "ERROR ")))


def _without_timings(line: str) -> str:
    clean = _BARE_DURATION.sub("", _CLOCK.sub("", _TIMING.sub("", line)))
    return re.sub(r"[=_-]{2,}|\s+", " ", clean).strip()


def failure_signature(output: str, code: int) -> str:
    """Failed test ids (sorted) when present, else the last line without timings."""
    lines = [line.strip() for line in _ANSI.sub("", output).splitlines() if line.strip()]
    failed = _failed_ids(lines)
    if failed:
        return "; ".join(failed)
    return (_without_timings(lines[-1]) if lines else "") or f"exit {code}"
