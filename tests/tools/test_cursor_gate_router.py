from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from tools.cursor_gate_router import (
    GateSpec,
    discover_gate,
    effective_gate,
    fingerprint,
    git_state,
    hook_result,
    run_gate,
)


def test_explicit_config_wins_over_detected_stack(tmp_path: Path) -> None:
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "dev_check.ps1").write_text("", encoding="utf-8")
    (tmp_path / ".ai-quality-gates.json").write_text(
        json.dumps({"quick": "python custom_check.py", "timeout": 45}), encoding="utf-8"
    )

    assert discover_gate(tmp_path) == GateSpec(
        command="python custom_check.py", source=".ai-quality-gates.json", timeout=45
    )


def test_explicit_disable_opts_repository_out(tmp_path: Path) -> None:
    (tmp_path / ".ai-quality-gates.json").write_text(
        json.dumps({"enabled": False}), encoding="utf-8"
    )

    assert discover_gate(tmp_path) is None


def test_canonical_windows_gate_has_priority(tmp_path: Path) -> None:
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "dev_check.ps1").write_text("param([switch]$Quick)\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")

    assert discover_gate(tmp_path) == GateSpec(
        command="pwsh -NoProfile -File tools/dev_check.ps1 -Quick",
        source="tools/dev_check.ps1",
        timeout=180,
    )


def test_canonical_windows_gate_without_quick_parameter_runs_full_entry(tmp_path: Path) -> None:
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "dev_check.ps1").write_text("Write-Host 'GATE GREEN'\n", encoding="utf-8")

    assert discover_gate(tmp_path) == GateSpec(
        command="pwsh -NoProfile -File tools/dev_check.ps1",
        source="tools/dev_check.ps1",
        timeout=180,
    )


def test_node_script_uses_declared_package_manager(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"check": "eslint .", "test": "vitest"}}), encoding="utf-8"
    )
    (tmp_path / "pnpm-lock.yaml").write_text("lockfileVersion: '9'\n", encoding="utf-8")

    assert discover_gate(tmp_path) == GateSpec(
        command="pnpm run check", source="package.json#scripts.check", timeout=180
    )


def test_python_fallback_prefers_uv_when_locked(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()

    assert discover_gate(tmp_path) == GateSpec(
        command="uv run --offline --no-sync pytest -q",
        source="pyproject.toml+tests",
        timeout=180,
    )


def test_unknown_repository_uses_universal_git_baseline(tmp_path: Path) -> None:
    assert discover_gate(tmp_path) == GateSpec(
        command="git diff --check && git diff --cached --check",
        source="global-baseline",
        timeout=60,
    )


def test_untrusted_repository_cannot_auto_run_native_command(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "remote",
            "add",
            "origin",
            "https://github.com/external/demo.git",
        ],
        check=True,
    )
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"test": "python dangerous.py"}}), encoding="utf-8"
    )
    trust = tmp_path / "trust.json"
    trust.write_text(json.dumps({"trusted_github_owners": ["SanHsien"]}), encoding="utf-8")

    assert effective_gate(tmp_path, trust) == GateSpec(
        command="git diff --check && git diff --cached --check",
        source="untrusted-baseline",
        timeout=60,
    )


def test_trusted_owner_uses_repository_native_gate(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "remote",
            "add",
            "origin",
            "https://github.com/SanHsien/demo.git",
        ],
        check=True,
    )
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"test": "vitest"}}), encoding="utf-8"
    )
    trust = tmp_path / "trust.json"
    trust.write_text(json.dumps({"trusted_github_owners": ["SanHsien"]}), encoding="utf-8")

    assert effective_gate(tmp_path, trust) == GateSpec(
        command="npm run test", source="package.json#scripts.test", timeout=180
    )


def test_gate_result_records_machine_evidence(tmp_path: Path) -> None:
    spec = GateSpec(command="python check.py", source="test", timeout=10)

    result = run_gate(
        tmp_path,
        spec,
        runner=lambda *_args, **_kwargs: (0, "QUALITY GREEN", ""),
    )

    assert result.status == "passed"
    assert result.exit_code == 0
    assert result.output == "QUALITY GREEN"
    assert fingerprint(tmp_path, spec, git_state="abc") == fingerprint(
        tmp_path, spec, git_state="abc"
    )


def test_baseline_rejects_staged_whitespace_errors(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    target = tmp_path / "bad.txt"
    target.write_text("trailing space \n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "bad.txt"], check=True)
    spec = GateSpec("git diff --check && git diff --cached --check", "untrusted-baseline", 60)

    result = run_gate(tmp_path, spec)

    assert result.status == "failed"
    assert result.exit_code != 0
    assert "trailing whitespace" in result.output


def test_untrusted_baseline_does_not_execute_repo_local_git_bat(
    tmp_path: Path, monkeypatch
) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    marker = tmp_path / "EXECUTED"
    (tmp_path / "git.bat").write_text(f'@echo bad>"{marker}"\r\n', encoding="utf-8")
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    spec = GateSpec("git diff --check && git diff --cached --check", "untrusted-baseline", 60)

    result = run_gate(tmp_path, spec)

    assert result.status == "passed"
    assert not marker.exists()


def test_untrusted_repo_cannot_hijack_git_during_trust_or_state_probes(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "remote",
            "add",
            "origin",
            "git@evilgithub.com:SanHsien/pwn.git",
        ],
        check=True,
    )
    trust = repo / "trust.json"
    trust.write_text(json.dumps({"trusted_github_owners": ["SanHsien"]}), encoding="utf-8")
    marker = repo / "EXECUTED"
    (repo / "git.bat").write_text(f'@echo bad>"{marker}"\r\n', encoding="utf-8")
    source_root = Path(__file__).resolve().parents[2]
    env = dict(os.environ)
    env["PATH"] = f"{repo}{os.pathsep}{env['PATH']}"
    env["PYTHONPATH"] = str(source_root)
    code = (
        "from pathlib import Path; "
        "from tools.cursor_gate_router import effective_gate, git_state; "
        "repo=Path.cwd(); "
        "spec=effective_gate(repo, repo/'trust.json'); "
        "git_state(repo); "
        "print(spec.source)"
    )

    proc = subprocess.run(
        [sys.executable, "-c", code], cwd=repo, env=env, capture_output=True, text=True
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "untrusted-baseline"
    assert not marker.exists()


def test_git_state_changes_when_untracked_file_content_changes(tmp_path: Path) -> None:
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    target = tmp_path / "new.py"
    target.write_text("print(1)\n", encoding="utf-8")
    before = git_state(tmp_path)

    target.write_text("print(222)\n", encoding="utf-8")

    assert git_state(tmp_path) != before


def test_git_state_hashes_same_size_untracked_content(tmp_path: Path) -> None:
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    target = tmp_path / "new.py"
    target.write_text("print(1)\n", encoding="utf-8")
    stamp = target.stat().st_mtime_ns
    before = git_state(tmp_path)

    target.write_text("print(2)\n", encoding="utf-8")
    target.touch()
    os.utime(target, ns=(stamp, stamp))

    assert git_state(tmp_path) != before


def test_parallel_evaluations_do_not_collide_on_state_temp_file(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    env = dict(os.environ)
    env.update({"HOME": str(home), "USERPROFILE": str(home)})
    code = (
        "from pathlib import Path; "
        "from tools.cursor_gate_router import evaluate; "
        f"raise SystemExit(0 if evaluate(Path({str(repo)!r}), False).status == 'passed' else 1)"
    )

    def invoke(_index: int) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)

    with ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(invoke, range(30)))

    assert all(result.returncode == 0 for result in results), [
        result.stderr for result in results if result.returncode != 0
    ]


def test_failed_cursor_hook_returns_followup_message() -> None:
    response = hook_result("failed", "pytest failed", "python -m pytest -q")

    assert response == {
        "followup_message": (
            "AI quality gate failed (`python -m pytest -q`). "
            "Fix it and rerun before claiming completion:\npytest failed"
        )
    }


def test_passed_or_unconfigured_hook_is_silent() -> None:
    assert hook_result("passed", "", "cmd") == {}
    assert hook_result("unconfigured", "", "") == {}
