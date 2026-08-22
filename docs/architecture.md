# 架構

## 資料流

```text
examples/order.json
        |
        v
quality_gate_demo.cli  --->  quality_gate_demo.pricing
        |                          |
        v                          v
 integration / QA smoke       unit / mutation

Gherkin acceptance ---------> externally visible behavior
quality scripts ------------> coverage, complexity, size, JUnit evidence

trigger -> isolated maker -> deterministic gates -> independent checker
              ^                       |                    |
              +------- compact state -+------ stop/escalate+
```

`pricing` 是 domain policy，只依賴標準函式庫；`cli` 是輸入輸出 adapter。Import Linter 明確禁止 domain 反向依賴 adapter。

## 目錄責任

- `src/quality_gate_demo/`：最小可執行 domain 與 CLI。
- `tests/unit/`：純規則與邊界。
- `tests/integration/`：檔案輸入與 CLI 輸出契約。
- `features/`：人可檢視的 Gherkin 驗收規格。
- `tools/`：Windows/Linux 開發入口、QA、量測與 fail-closed checker。
- `.github/`：跨平台 CI、安全掃描、依賴更新與協作模板。
- `.agents/skills/quality-loop/`：可重用的有界 agent loop 操作契約。
- `loop-policy.toml`：可機械驗證的成本、隔離、驗證與人工核准政策。
- `loop-state/`：未追蹤的最小 runtime state；只保留 README。
- `artifacts/`：本機產生且不提交的驗收證據。

## 擴充方式

新增 domain 時先補 Gherkin 或單元失敗案例，再新增 implementation。若新增 adapter，更新 Import Linter contract；若新模組需要超過 200 行，先拆分責任，不直接調高門檻。
