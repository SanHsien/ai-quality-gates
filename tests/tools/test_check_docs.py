from __future__ import annotations

from pathlib import Path

from tools.check_docs import find_broken_links, iter_markdown_files


def test_docs_checker_accepts_existing_local_and_external_links(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text("# Guide\n", encoding="utf-8")
    readme = tmp_path / "README.md"
    readme.write_text(
        "[guide](docs/guide.md) [section](#section) [web](https://example.com)\n",
        encoding="utf-8",
    )

    assert find_broken_links(tmp_path, [readme]) == []


def test_docs_checker_reports_missing_relative_target(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("[missing](docs/missing.md)\n", encoding="utf-8")

    broken = find_broken_links(tmp_path, [readme])

    assert len(broken) == 1
    assert broken[0].source == readme
    assert broken[0].target == "docs/missing.md"


def test_docs_discovery_ignores_every_virtual_environment_variant(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# Included\n", encoding="utf-8")
    generated = tmp_path / ".venv-mutation" / "site-packages"
    generated.mkdir(parents=True)
    (generated / "README.md").write_text("[broken](missing.md)\n", encoding="utf-8")

    assert iter_markdown_files(tmp_path) == [readme]
