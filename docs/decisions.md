# 設計決策

## 2026-08-22：使用 Python 與 uv

Python 的 pytest、Behave、coverage、Radon、Import Linter 與 mutmut 能覆蓋行為、結構與測試有效性等主要關卡。uv 提供 lockfile、跨平台安裝與可重現命令，Windows 使用 `.venv`，Linux/WSL 使用獨立環境，避免交叉污染。

## 2026-08-22：保留分層 gate

驗證深度應依 criticality 調整。專案因此分成 Quick、Full、Mutation，不把最昂貴的 mutation 放進每次本機迭代。

## 2026-08-22：量化指標採 fail-closed，但不宣稱證明正確

coverage、complexity、module size 與 mutation 都有明確門檻，缺少報告或 total 為零時視為失敗。文件同時保留各指標的盲點，避免 Goodhart's law 式追逐分數。

## 2026-08-22：Loop 預設停用，政策先於 runner

Loop Engineering 的價值在可持續的反饋與狀態，不在無限重試。本 repo 先交付可測試的 `loop-policy.toml` 與 checker，強制 iteration、time、token、隔離、獨立 verifier、人工核准與 terminal states；在尚未以人工觸發證明穩定前，不加入 scheduler 或無人值守 runner。
