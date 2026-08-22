# 設計決策

## 2026-08-22：使用 Python 與 uv

Python 的 pytest、Behave、coverage、Radon、Import Linter 與 mutmut 可對應文章的主要關卡。uv 提供 lockfile、跨平台安裝與可重現命令，Windows 使用 `.venv`，Linux/WSL 使用獨立環境，避免交叉污染。

## 2026-08-22：保留分層 gate

Martin 的後續脈絡強調 criticality，也曾反思測試負載。專案因此分成 Quick、Full、Mutation，不把最昂貴的 mutation 放進每次本機迭代。

## 2026-08-22：量化指標採 fail-closed，但不宣稱證明正確

coverage、complexity、module size 與 mutation 都有明確門檻，缺少報告或 total 為零時視為失敗。文件同時保留各指標的盲點，避免 Goodhart's law 式追逐分數。
