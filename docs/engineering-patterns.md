# 可移植的工程模式

本文件只保留能直接套用的工程模式，不記錄來源專案、盤點數量或採用率。

| 方法 | 本 repo 的採用方式 | 解決的風險 |
| --- | --- | --- |
| 單元／整合測試 | pytest unit + integration | 局部規則與模組協作錯誤 |
| Coverage | 95% line/branch fail-under + JSON | 未執行路徑 |
| 型別檢查 | strict mypy | 介面與資料形狀漂移 |
| Lint/format | Ruff lint + format | 一致性與常見靜態缺陷 |
| 安全／供應鏈 | CodeQL、pip-audit、Dependabot | 已知漏洞與依賴風險 |
| Smoke | 唯一 CLI QA smoke | 公開入口與封裝失效 |
| 跨平台 gate | PowerShell 與 Bash 開發入口 | Windows、Linux/WSL 行為分歧 |
| BDD/Gherkin | Behave acceptance scenarios | 需求與實作脫節 |
| 複雜度指標 | Xenon A 級 + JSON summary | 高分支與維護風險 |
| 文件 gate | 相對連結檢查 | 文件入口失效 |
| Mutation gate | mutmut 100% gate | 測試只執行卻不偵錯 |
| 架構依賴 contract | Import Linter contract | 模組依賴逆轉 |
| Agent loop 邊界 | 有界 policy、獨立 verifier、最小 state 與硬停止條件 | 無界重試、自我驗證與權限擴張 |

## 採納的成熟做法

- Windows PowerShell 是主要本機入口，Ubuntu CI 補足 Unix-only 工具。
- Quick 與 Full 分流，昂貴驗證不阻塞每次迭代。
- workflow 使用最小 permissions、concurrency、timeout 與可重現 lockfile。
- 產生機械可讀 evidence，不只輸出「綠燈」。
- 以 Quick/Full、Windows-first 與最小 smoke 原則，把 loop 的成本與停止條件做成 fail-closed contract。
- CodeQL、dependency audit、Dependabot、issue/PR templates 與 release hygiene 放入 repo。
- 測試公開入口、文件相對連結與 package build，避免只測內部 helper。

## 關卡組合原則

各關卡處理不同的失敗模式，不能用 coverage 取代 mutation，也不能用行為測試取代 architecture contract。本 repo 把 mutation 與架構契約設為第一級 gate，並清楚限制 mutation 僅在 Linux/WSL 執行。
