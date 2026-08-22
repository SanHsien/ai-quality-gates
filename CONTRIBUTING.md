# 貢獻指南

## 開發流程

1. 先讀 [AGENTS.md](AGENTS.md) 與 [品質關卡](docs/quality-gates.md)。
2. 新行為先加入失敗測試或 Gherkin scenario。
3. 做最小實作，跑 Quick gate。
4. 交付前跑 Full gate；核心規則或測試策略變更另跑 Mutation。

```powershell
pwsh -NoProfile -File tools\bootstrap_dev.ps1
pwsh -NoProfile -File tools\dev_check.ps1 -Quick
pwsh -NoProfile -File tools\dev_check.ps1
```

PR 必須說明需求／邊界、實際執行指令、量化摘要，以及未由自動化涵蓋的風險。不要只貼 coverage 百分比。
