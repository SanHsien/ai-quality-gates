# 既有 repo 方法盤點

## 範圍與方法

2026-08-22 對 `C:\Users\SanHsien\OneDrive\文件\GitHub` 下、排除本 repo 的 24 個 Git repo 做唯讀掃描。以 manifest、GitHub Actions、`tools/`、`scripts/` 與維護文件中的關鍵字彙整；這是工程方法盤點，不代表每個 workflow 當時的遠端執行狀態。

掃描範圍：`agentdeck`、`ai-content-factory`、`book-to-skill`、`chatgpt-sidebar`、`github-stars-organizer-playbook`、`gpt-ai-assistant`、`gpt-ai-assistant-docs`、`harness-guard`、`human-writing`、`key-checkout-system`、`n8n`、`openshelf`、`openshelf-personal`、`paulsha-cortex`、`public-apis`、`SanHsien`、`sticker-forge`、`student-achievement-upload-system`、`video-autopilot-kit`、`voicetype`、`voxavatar`、`xiaoke-agent`、`xiaoke-claude-memory`、`yt_fetch`。

## 彙整結果

| 方法 | 命中 repo 數 | 本 repo 的採用方式 |
| --- | ---: | --- |
| 單元／自動測試 | 20/24 | pytest unit + integration |
| Coverage | 18/24 | 95% line/branch fail-under + JSON |
| 型別檢查 | 16/24 | strict mypy |
| Lint/format | 15/24 | Ruff lint + format |
| 安全／供應鏈 | 18/24 | CodeQL、pip-audit、Dependabot |
| Smoke/E2E/health | 18/24 | 唯一 CLI QA smoke |
| Windows gate | 10/24 | `tools/dev_check.ps1` 與 bootstrap |
| BDD/Gherkin | 3/24 | Behave acceptance scenarios |
| 複雜度指標 | 5/24 | Xenon A 級 + JSON summary |
| 文件 gate | 2/24 | 自帶相對連結檢查 |
| Mutation gate | 0/24 | 新增 mutmut 100% gate |
| 架構依賴 contract | 0/24 | 新增 Import Linter contract |

## 採納的成熟做法

- Windows PowerShell 是主要本機入口，Ubuntu CI 補足 Unix-only 工具。
- Quick 與 Full 分流，昂貴驗證不阻塞每次迭代。
- workflow 使用最小 permissions、concurrency、timeout 與可重現 lockfile。
- 產生機械可讀 evidence，不只輸出「綠燈」。
- CodeQL、dependency audit、Dependabot、issue/PR templates 與 release hygiene 放入 repo。
- 測試公開入口、文件相對連結與 package build，避免只測內部 helper。

## 新增而非複製的部分

既有 repo 尚未形成 mutation 與 architecture contract 的一致做法。本 repo 把兩者設為第一級 gate，並清楚限制 mutation 僅在 Linux/WSL 執行。
