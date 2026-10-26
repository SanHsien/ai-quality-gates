"""Regressions found by the second-round deep scan (one test per defect)."""

from __future__ import annotations

import hashlib
import http.client
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tools import check_dependency_freshness as freshness
from tools import cursor_gate_router as router
from tools.check_docs import find_broken_links, iter_markdown_files
from tools.check_loop_policy import validate_loop_policy
from tools.check_module_size import main as module_size_main
from tools.check_mutation_score import evaluate_mutation_stats
from tools.cursor_gate_core import _default_runner

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_gate_timeout_returns_even_when_a_grandchild_keeps_the_pipe_open(tmp_path: Path) -> None:
    command = f'"{sys.executable}" -c "import time; time.sleep(25)"'
    started = time.monotonic()

    code, _out, err = _default_runner(command, tmp_path, 2)

    assert code == 124
    assert "timed out" in err
    assert time.monotonic() - started < 12


def test_docs_discovery_does_not_judge_the_directories_above_the_root(tmp_path: Path) -> None:
    root = tmp_path / "artifacts" / "repo"
    root.mkdir(parents=True)
    readme = root / "README.md"
    readme.write_text("# Included\n", encoding="utf-8")

    assert iter_markdown_files(root) == [readme]


def test_link_with_wrong_letter_case_is_broken_on_every_platform(tmp_path: Path) -> None:
    (tmp_path / "Guide.md").write_text("# g\n", encoding="utf-8")
    readme = tmp_path / "README.md"
    readme.write_text("[g](guide.md)\n", encoding="utf-8")

    assert [b.target for b in find_broken_links(tmp_path, [readme])] == ["guide.md"]


def test_module_size_fails_on_a_path_that_does_not_exist(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert module_size_main([str(tmp_path / "no_such_dir")]) != 0
    assert "GREEN" not in capsys.readouterr().out


def test_freshness_skips_include_group_entries(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[dependency-groups]\ndev = ["ruff>=0.16,<1"]\nall = [{include-group = "dev"}]\n',
        encoding="utf-8",
    )

    assert [d.name for d in freshness.load_declarations(pyproject)] == ["ruff"]


def test_freshness_treats_a_truncated_response_as_no_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken(*_args: object, **_kwargs: object) -> object:
        raise http.client.IncompleteRead(b"{")

    monkeypatch.setattr(freshness.urllib.request, "urlopen", broken)

    assert freshness.fetch_latest("ruff") is None


def test_policy_that_is_not_utf8_fails_closed_with_a_violation(tmp_path: Path) -> None:
    policy = tmp_path / "loop-policy.toml"
    policy.write_bytes(b"\xff\xfe\x00\x80")

    assert validate_loop_policy(policy)


def _stats(tmp_path: Path, **values: int) -> Path:
    path = tmp_path / "stats.json"
    path.write_text(json.dumps(values), encoding="utf-8")
    return path


def test_mutation_score_is_not_rounded_up_to_the_minimum(tmp_path: Path) -> None:
    stats = _stats(tmp_path, total=100_001, killed=100_000)

    assert evaluate_mutation_stats(stats, minimum_score=100.0)["passed"] is False


def test_mutation_stats_with_more_killed_than_total_are_rejected(tmp_path: Path) -> None:
    stats = _stats(tmp_path, total=10, killed=11)

    assert evaluate_mutation_stats(stats, minimum_score=100.0)["passed"] is False


def test_loop_verifier_survives_undecodable_output_under_a_legacy_code_page() -> None:
    script = (
        "from tools.loop_runner import _default_verifier;"
        "import sys;"
        "code, output = _default_verifier(sys.argv[1]);"
        "print(code, bool(output.strip()))"
    )
    child = "import sys; sys.stderr.buffer.write(bytes([0x88, 10])); sys.exit(3)"
    gate = f'"{sys.executable}" -c "{child}"'

    done = subprocess.run(
        [sys.executable, "-X", "utf8=0", "-c", script, gate],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )

    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    assert done.stdout.split() == [b"3", b"True"]


def test_evaluate_ignores_a_malformed_cache_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    state_file = tmp_path / "state.json"
    key = hashlib.sha256(str(repo.resolve()).encode()).hexdigest()
    state_file.write_text(json.dumps({key: ["not", "a", "dict"]}), encoding="utf-8")
    spec = router.GateSpec("echo ok", "test")
    monkeypatch.setattr(router, "_state_path", lambda: state_file)
    monkeypatch.setattr(router, "effective_gate", lambda _repo: spec)
    monkeypatch.setattr(router, "git_state", lambda _repo: "state")
    monkeypatch.setattr(
        router, "run_gate", lambda _r, s: router.GateResult("passed", s.command, s.source, 0, "")
    )

    assert router.evaluate(repo).status == "passed"
