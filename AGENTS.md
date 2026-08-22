# AGENTS.md

給 Codex 與其他自動化代理在本 repo 工作時的約束。

## 核心原則

- 行為變更先寫失敗的 unit、integration 或 Gherkin case，再做最小實作。
- 不以 coverage 綠燈替代需求檢查；修改核心規則時執行 mutation gate。
- `quality_gate_demo.pricing` 不可依賴 CLI 或其他 delivery adapter。
- 每個維護 Python module 不得超過 200 個非空、非 comment-only 行。
- 不降低 coverage、complexity、module-size 或 mutation 門檻來讓變更通過。
- 不提交 `.venv*`、`artifacts/`、`mutants/`、coverage、token、cookie 或密碼。

## 自動化迴圈

- 可重複且能由機械證據驗收的工作，才可使用 [quality-loop skill](.agents/skills/quality-loop/SKILL.md)。
- 啟動前必須符合 `loop-policy.toml`；預設停用，不得自行改成無人值守執行。
- maker 與 checker 必須分離；不以 agent 自評或 coverage 單一數字作為通過證據。
- 達到成功、成本上限、重複失敗或人工核准邊界時立即停止。
- 不允許 loop 自動合併、直接推送 `main`、處理秘密或核准高風險外部寫入。

## 驗證

Windows 日常：

```powershell
pwsh -NoProfile -File tools\dev_check.ps1 -Quick
```

交付前：

```powershell
pwsh -NoProfile -File tools\dev_check.ps1
pwsh -NoProfile -File tools\dev_check.ps1 -Mutation
```

高成本關卡取得一次權威綠燈即停止。失敗時只重跑相關 focused test，修完後再跑一次完整 gate。
