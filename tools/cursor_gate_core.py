"""Pure discovery and execution primitives for the Cursor quality-gate adapter."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

try:
    from tools.cursor_gate_baseline import run_baseline
except ModuleNotFoundError:  # installed flat beside this module
    from cursor_gate_baseline import run_baseline  # type: ignore[import-not-found,no-redef]

CONFIG = ".ai-quality-gates.json"
DEFAULT_TIMEOUT = 180


@dataclass(frozen=True)
class GateSpec:
    command: str
    source: str
    timeout: int = DEFAULT_TIMEOUT


@dataclass(frozen=True)
class GateResult:
    status: str
    command: str
    source: str
    exit_code: int | None
    output: str


def _configured_gate(repo: Path) -> GateSpec | None:
    path = repo / CONFIG
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return None
    if not isinstance(data, dict) or data.get("enabled", True) is False:
        return None
    command = str(data.get("quick") or data.get("cmd") or "").strip()
    if not command:
        return None
    timeout = data.get("timeout", DEFAULT_TIMEOUT)
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout < 1:
        timeout = DEFAULT_TIMEOUT
    return GateSpec(command, CONFIG, timeout)


def _powershell_gate(repo: Path) -> GateSpec | None:
    path = repo / "tools/dev_check.ps1"
    if not path.is_file():
        return None
    try:
        supports_quick = "$Quick" in path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        supports_quick = False
    suffix = " -Quick" if supports_quick else ""
    return GateSpec(f"pwsh -NoProfile -File tools/dev_check.ps1{suffix}", "tools/dev_check.ps1")


def _package_manager(repo: Path) -> str:
    if (repo / "yarn.lock").exists():
        return "yarn"
    if (repo / "bun.lock").exists() or (repo / "bun.lockb").exists():
        return "bun"
    return "pnpm" if (repo / "pnpm-lock.yaml").exists() else "npm"


def _node_gate(repo: Path) -> GateSpec | None:
    package = repo / "package.json"
    if not package.is_file():
        return None
    try:
        scripts = json.loads(package.read_text(encoding="utf-8")).get("scripts", {})
    except (OSError, ValueError, AttributeError, UnicodeError):
        return None
    if not isinstance(scripts, dict):
        return None
    for name in ("verify", "check", "test"):
        if not scripts.get(name):
            continue
        manager = _package_manager(repo)
        command = f"{manager} {name}" if manager == "yarn" else f"{manager} run {name}"
        return GateSpec(command, f"package.json#scripts.{name}")
    return None


def _script_gate(repo: Path) -> GateSpec | None:
    for source, command in (
        ("tools/dev_check.sh", "sh tools/dev_check.sh"),
        ("scripts/run_tests.sh", "sh scripts/run_tests.sh"),
    ):
        if (repo / source).is_file():
            return GateSpec(command, source)
    return None


def _python_gate(repo: Path) -> GateSpec | None:
    if not (repo / "pyproject.toml").is_file() or not (repo / "tests").is_dir():
        return None
    command = (
        "uv run --offline --no-sync pytest -q"
        if (repo / "uv.lock").is_file()
        else "python -m pytest -q"
    )
    return GateSpec(command, "pyproject.toml+tests")


def _ecosystem_gate(repo: Path) -> GateSpec | None:
    for marker, command in (
        ("go.mod", "go test ./..."),
        ("Cargo.toml", "cargo test --quiet"),
        ("pom.xml", "mvn -q test"),
        ("gradlew.bat", "gradlew.bat test"),
        ("gradlew", "./gradlew test"),
    ):
        if (repo / marker).exists():
            return GateSpec(command, marker)
    return None


def discover_gate(repo: Path) -> GateSpec | None:
    repo = repo.resolve()
    if (repo / CONFIG).is_file():
        return _configured_gate(repo)
    for finder in (_powershell_gate, _script_gate, _node_gate, _python_gate, _ecosystem_gate):
        if gate := finder(repo):
            return gate
    return GateSpec("git diff --check && git diff --cached --check", "global-baseline", 60)


def _default_runner(command: str, repo: Path, timeout: int) -> tuple[int, str, str]:
    env = dict(os.environ)
    env.update(
        {
            "UV_OFFLINE": "1",
            "PIP_NO_INDEX": "1",
            "npm_config_offline": "true",
            "GOPROXY": "off",
            "CARGO_NET_OFFLINE": "true",
        }
    )
    try:
        proc = subprocess.run(
            command, cwd=repo, shell=True, capture_output=True, timeout=timeout, env=env
        )
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or b"") + (exc.stderr or b"")
        return 124, out.decode("utf-8", "replace"), "gate timed out"
    except OSError as exc:
        return 126, "", str(exc)
    return (
        proc.returncode,
        proc.stdout.decode("utf-8", "replace"),
        proc.stderr.decode("utf-8", "replace"),
    )


def run_gate(
    repo: Path,
    spec: GateSpec,
    runner: Callable[[str, Path, int], tuple[int, str, str]] = _default_runner,
) -> GateResult:
    if spec.source in {"global-baseline", "untrusted-baseline"}:
        code, stdout, stderr = run_baseline(repo, spec.timeout)
    else:
        code, stdout, stderr = runner(spec.command, repo, spec.timeout)
    output = (stdout + ("\n" if stdout and stderr else "") + stderr).strip()[-4000:]
    return GateResult("passed" if code == 0 else "failed", spec.command, spec.source, code, output)


def fingerprint(repo: Path, spec: GateSpec, git_state: str) -> str:
    raw = f"{repo.resolve()}\0{spec.command}\0{git_state}".encode()
    return hashlib.sha256(raw).hexdigest()


def hook_result(status: str, output: str, command: str) -> dict[str, str]:
    if status not in {"failed", "error"}:
        return {}
    detail = output[-2000:] or "gate exited without diagnostic output"
    return {
        "followup_message": (
            f"AI quality gate failed (`{command}`). Fix it and rerun "
            f"before claiming completion:\n{detail}"
        )
    }
