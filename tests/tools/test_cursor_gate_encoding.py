"""Git output is UTF-8 whatever the Windows ANSI code page is (cp950, cp932, ...)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GIT = ("git", "-c", "user.name=t", "-c", "user.email=t@example.invalid")


def _git(repo: Path, *args: str) -> None:
    subprocess.run([*GIT, "-C", str(repo), *args], check=True, capture_output=True)


def _legacy_codepage(script: str, *args: str) -> subprocess.CompletedProcess[bytes]:
    """Run script with UTF-8 mode off, as Cursor runs the installed hook."""

    return subprocess.run(
        [sys.executable, "-X", "utf8=0", "-c", script, *args],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )


def _repo_with_cjk_edit(parent: Path, name: str = "repo") -> Path:
    repo = parent / name
    repo.mkdir()
    _git(repo, "init", "-q")
    note = repo / "note.txt"
    note.write_text("三賢測試\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "init")
    note.write_text("三賢測試，修改後的內容\n", encoding="utf-8")
    return repo


def test_git_state_survives_cjk_diff_under_a_legacy_code_page(tmp_path: Path) -> None:
    repo = _repo_with_cjk_edit(tmp_path)

    done = _legacy_codepage(
        "import sys; from pathlib import Path; from tools.cursor_gate_router import git_state;"
        "print(len(git_state(Path(sys.argv[1]))))",
        str(repo),
    )

    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")


def test_baseline_survives_cjk_whitespace_error_under_a_legacy_code_page(tmp_path: Path) -> None:
    repo = _repo_with_cjk_edit(tmp_path)
    (repo / "note.txt").write_text("三賢測試，行尾空白   \n", encoding="utf-8")

    done = _legacy_codepage(
        "import sys, json; from pathlib import Path;"
        "from tools.cursor_gate_baseline import run_baseline;"
        "print(json.dumps(run_baseline(Path(sys.argv[1]), 30)))",
        str(repo),
    )

    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    code, stdout, _stderr = json.loads(done.stdout)
    assert code != 0
    assert "三賢測試" in stdout


def test_hook_resolves_a_repository_whose_path_has_cjk_characters(tmp_path: Path) -> None:
    repo = _repo_with_cjk_edit(tmp_path, name="專案三賢")

    done = _legacy_codepage(
        "import sys; from pathlib import Path; from tools.cursor_gate_router import _payload_repo;"
        "sys.stdout.buffer.write(str(_payload_repo({'cwd': sys.argv[1]})).encode('utf-8'))",
        str(repo),
    )

    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    assert Path(done.stdout.decode("utf-8").strip()).resolve() == repo.resolve()
