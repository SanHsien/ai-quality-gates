# AI Quality Gates

[English](README.en.md)

以可執行規格、自動化測試、工程量化指標與有界迴圈約束 AI 輔助開發的 Python 參考專案。它不是「測試綠燈就可免責」的宣言，而是一套把需求、邊界、架構、成本上限與停止條件做成可重現證據的最小實作。

核心原則是把人工判斷集中在需求、邊界條件、風險分級與發布決策，並由可執行規格、分層測試、架構契約及量化門檻提供可重現的反證能力。完整原則與限制見 [工程原則](docs/engineering-principles.md)。

## 已落地的關卡

| 關卡 | 實作 | 目前門檻 |
| --- | --- | --- |
| 單元與整合測試 | pytest | 失敗、錯誤、跳過皆為 0 |
| 可執行規格 | Behave + Gherkin | 所有 scenario 通過 |
| QA 流程 | 真實 CLI smoke | 唯一範例輸出精準符合契約 |
| 測試覆蓋率 | coverage.py | line + branch 合計至少 95% |
| 突變測試 | mutmut | 100%，不得有 survivor 或未測 mutant |
| 圈複雜度 | Radon/Xenon | domain block A 級（1–5）；工具 block 至多 B 級（6–10），module/平均 A 級 |
| 模組大小 | 自帶 fail-closed checker | 每個維護模組至多 200 行 |
| 依賴結構 | Import Linter | domain 不可反向依賴 CLI adapter |
| 靜態品質 | Ruff + strict mypy | 0 finding |
| 供應鏈與安全 | pip-audit + Dependabot + CodeQL | 高風險問題不得通過 |
| Agent loop 治理 | TOML policy + fail-closed checker | 有界成本、獨立 verifier、禁止 auto-merge 與高風險自行核准 |

詳細理由與盲點見 [品質關卡說明](docs/quality-gates.md)。

## Loop Engineering

本 repo 也把 Loop Engineering 落成機械化治理，而不只是描述抽象流程：

- [`loop-policy.toml`](loop-policy.toml) 定義 iteration、時間、token、平行工作區與重複失敗的硬上限。
- [`tools/check_loop_policy.py`](tools/check_loop_policy.py) 在 Quick/Full gate 驗證隔離、maker/checker 分離、state、connector 與人工核准邊界。
- [repo-local quality-loop skill](.agents/skills/quality-loop/SKILL.md) 規範 agent 如何開始、留下證據與停止。
- [Loop Engineering 設計](docs/loop-engineering.md)說明五階段循環、六項基礎設施、適用判準與停止規則。

安全預設是 `loop.enabled = false`。專案目前提供可驗證 contract，不提供無界限 runner，也不自動推送、合併或部署。

## 快速開始（Windows）

需要 Python 3.12、[uv](https://docs.astral.sh/uv/) 與 PowerShell 7：

```powershell
pwsh -NoProfile -File tools\bootstrap_dev.ps1
pwsh -NoProfile -File tools\dev_check.ps1 -Quick
pwsh -NoProfile -File tools\dev_check.ps1
```

mutation testing 的 mutmut 不支援原生 Windows，因此完整突變 gate 透過 WSL 執行：

```powershell
pwsh -NoProfile -File tools\dev_check.ps1 -Mutation
```

Linux／WSL：

```bash
bash tools/bootstrap_dev.sh
bash tools/dev_check.sh
bash tools/mutation_check.sh
```

## 示範程式

repo 內有一個刻意保持小型的訂單報價 domain。先由 [Gherkin 規格](features/order_quote.feature)定義折扣、免運與快速配送邊界，再由單元、整合與 QA smoke 交叉驗證：

```powershell
uv run quality-gate-demo quote --input examples\order.json
```

這個 domain 只是驗證載體；真正的交付是可移植到其他 Python repo 的關卡、CI 與量化證據格式。

## 分層執行

- `Quick`：格式、lint、typing、架構、pytest、Gherkin、QA、複雜度與模組大小。
- `Full`：Quick 加 coverage/JUnit JSON、文件連結、品質摘要、dependency audit 與 package build。
- `Mutation`：Full 加 Linux/WSL mutmut；適合高風險變更、排程或 merge 前驗收。

`Full` 會把 `coverage.json`、`junit.xml` 與 `quality-summary.json` 寫入未追蹤的 `artifacts/`。CI 也會保存這些證據。

## 專案文件

- [架構](docs/architecture.md)
- [品質關卡與責任邊界](docs/quality-gates.md)
- [工程原則](docs/engineering-principles.md)
- [Loop Engineering 與有界自治](docs/loop-engineering.md)
- [可移植的工程模式](docs/engineering-patterns.md)
- [設計決策](docs/decisions.md)
- [貢獻指南](CONTRIBUTING.md)
- [安全政策](SECURITY.md)

## 重要限制

高 coverage 只能證明程式被執行，mutation 只能檢查工具能產生的語意變化，Gherkin 也可能把錯誤需求寫得很精準。人仍須負責需求、關鍵邊界、風險分級、架構契約與發布決策；自動化關卡提供的是可重現的反證能力，不是正確性的數學證明。

## 相關工具

這四個 repo 各自治理 AI coding 的一層，可以單獨用，也可以疊起來用：

| 層 | Repo | 做什麼 |
| --- | --- | --- |
| 派工決策 | [agent-advisor](https://github.com/SanHsien/agent-advisor) | 風險分流路由 `solo`／`delegate`／`audit`／`full`：決定這件事要不要派工、派給誰 |
| 動作攔截 | [harness-guard](https://github.com/SanHsien/harness-guard) | agent runtime hook，在動手前後與收工時實際攔截危險指令、無證據宣稱、紅燈提交 |
| 產出品質 | **AI Quality Gates（你在這裡）** | 可執行規格與量化門檻：覆蓋率、突變測試、圈複雜度、依賴結構、有界 loop policy |
| 交付流程 | [paulsha-cortex](https://github.com/SanHsien/paulsha-cortex) | 多 Agent lifecycle：Candidate → Verify → Independent Review → Delivery → CompletionRecord |

相鄰但不同層：[opencodex](https://github.com/SanHsien/opencodex) 是供應商代理，決定這些 agent 背後能跑哪些 LLM，本身不約束 agent 行為。

## 授權

[MIT](LICENSE)
