# 品質關卡與責任邊界

## 關卡矩陣

| 問題 | 機械化證據 | 門檻 | 仍需人工負責 |
| --- | --- | --- | --- |
| 小單位是否符合規則 | pytest unit | 全綠、無 skip | 測試是否對應正確需求 |
| 公開邊界是否可用 | CLI integration + QA smoke | 唯一 smoke 精準通過 | 真實環境與營運風險 |
| 業務情境是否明確 | Gherkin/Behave | 全 scenario 通過 | Given/When/Then 是否漏掉情境 |
| 程式是否被充分執行 | line + branch coverage | 至少 95% | assertion 的品質與未建模需求 |
| 測試能否偵測語意變更 | mutmut | 100%，0 survivor/no-test/timeout | 等價 mutant 與工具未涵蓋變更 |
| 控制流程是否過度糾結 | Radon/Xenon | domain block A；工具 block 至多 B；module/平均 A | domain 是否被錯誤拆分 |
| 模組是否持續膨脹 | 自帶 size checker | 至多 200 維護行 | cohesion 與命名品質 |
| 分層是否被破壞 | Import Linter | contract kept | contract 本身是否完整 |
| 型別與常見錯誤 | strict mypy + Ruff | 0 finding | 動態資料與執行環境 |
| 依賴是否有已知漏洞 | pip-audit/Dependabot/CodeQL | 不接受阻斷問題 | exploitability 與修補優先順序 |
| 宣告是否落後現實 | 每月依賴新鮮度檢查 | 每個宣告都有下限，且沒有未處理的落後 | 升版時機與相容性風險 |
| Agent loop 是否有界 | policy checker | 成本、迭代、時間、隔離、獨立 verifier 與人工核准條件完整 | 是否值得自動化與最終發布責任 |

## 依賴新鮮度（每月）

`tools/check_dependency_freshness.py` 比對 `pyproject.toml` 的**宣告**與 PyPI 現行版，
每月 1 日由 `Dependency freshness` workflow 執行。它不看 `uv.lock`、不安裝、不改檔——
因為要問的正是「鎖檔已經跑在新版，但宣告還停在舊版」這個落差。

比對深度跟著宣告走：`>=0.12` 只比到次版，`>=6` 只比主版。這樣 `ruff>=0.12` 不會因為
0.12.4 每月誤報一次；報告一旦開始喊狼來了就沒人看。

紅燈有兩條正當出口，兩條都要留下理由：

- **維持宣告**：在宣告那一行加 `# freshness-hold: <理由>`。用於「這個下限就是我們要的」
  的長期政策。
- **已延後**：在 `.github/dependency-deferrals.json` 加
  `{"deferredLatest": "<當時看到的版本>", "reason": "<為什麼這次不升>"}`。
  PyPI 一超過該版本，延後自動失效、報告恢復提醒；沒有 `deferredLatest` 的條目直接忽略，
  因為那等於永久靜音。

**不要用調高下限來消音**：宣告是相容性承諾。要嘛升版並讓鎖檔與宣告一起前進，要嘛寫下
為什麼不升。

## 停止條件

每次 gate 只需要一次權威結果：

- Quick 顯示 `QUICK GATE GREEN` 即停止。
- Full 顯示 `FULL GATE GREEN`，且 `artifacts/quality-summary.json` 的 `passed` 為 `true` 即停止。
- Mutation 的 `mutmut-cicd-stats.json` 必須有非零 total，且 `check_mutation_score.py` 回傳 `passed: true`。
- Loop 在成功、預算用盡、重複失敗、驗證失敗或需要人工核准時必須進入 terminal state，不得自行續跑。

失敗時只針對缺少的證據重跑；不要為了提高信心重複跑已通過的高成本關卡。

## 為何不是 100% coverage

Martin 把 100% 視為漸近目標，但也明確指出 coverage 不等於 assertion 品質。本 repo 使用 95% branch-aware gate，再由 mutation、Gherkin 與 QA 補上不同失敗模式。門檻可以調高，但不應把數字當 KPI 或品質保證。

## 為何 mutation 是獨立層

mutmut 目前不支援原生 Windows。本 repo 在 GitHub Ubuntu runner 與 WSL 執行；日常 Quick/Full 不為了單一工具強迫切換平台。高風險邏輯、排程驗收與 merge 前候選才執行 Mutation。
