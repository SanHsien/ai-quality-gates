# 貢獻指南

## 開發流程

1. 先讀 [AGENTS.md](AGENTS.md) 與 [品質關卡](docs/quality-gates.md)；使用自動迴圈時另讀 [Loop Engineering](docs/loop-engineering.md)。
2. 從 `main` 建立短期 branch；不要直接推進主線。
3. 新行為先加入失敗測試或 Gherkin scenario。
4. 做最小實作，跑 Quick gate。
5. 交付前跑 Full gate；核心規則或測試策略變更另跑 Mutation。
6. 開 PR、讀完整 diff，等既有 CI / CodeQL 通過後再 squash merge。

```powershell
pwsh -NoProfile -File tools\bootstrap_dev.ps1
pwsh -NoProfile -File tools\dev_check.ps1 -Quick
pwsh -NoProfile -File tools\dev_check.ps1
```

PR 必須說明需求／邊界、實際執行指令、量化摘要，以及未由自動化涵蓋的風險。不要只貼 coverage 百分比。
