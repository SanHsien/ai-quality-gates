"""Validate repository-local links in Markdown files."""

from __future__ import annotations

import argparse
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+[^)]*)?\)")
IGNORED_PREFIXES = ("#", "http://", "https://", "mailto:", "data:")


@dataclass(frozen=True, slots=True)
class BrokenLink:
    source: Path
    target: str


def iter_markdown_files(root: Path) -> list[Path]:
    """Find maintained Markdown while excluding generated environments and artifacts."""

    return sorted(
        path
        for path in root.rglob("*.md")
        if not any(
            part.startswith(".venv") or part in {".git", "artifacts", "mutants"}
            for part in path.parts
        )
    )


def find_broken_links(repo_root: Path, markdown_files: Sequence[Path]) -> list[BrokenLink]:
    """Return local links whose target does not exist."""

    broken: list[BrokenLink] = []
    for source in markdown_files:
        content = source.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK.findall(content):
            if raw_target.startswith(IGNORED_PREFIXES):
                continue
            path_part = unquote(raw_target.split("#", maxsplit=1)[0])
            if not path_part:
                continue
            target = (source.parent / path_part).resolve()
            if not target.exists():
                broken.append(BrokenLink(source=source, target=raw_target))
    return broken


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    root = args.root.resolve()
    markdown_files = iter_markdown_files(root)
    broken = find_broken_links(root, markdown_files)
    if broken:
        for item in broken:
            print(f"{item.source.relative_to(root)}: missing {item.target}")
        return 1
    print(f"DOCS GREEN: {len(markdown_files)} Markdown files checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
