# 路線圖

> 本 repo 後續工作的單一真相源。做完一項，就在同一個 commit 刪掉那一列；新工作只加在這裡。
> 現況段的數字是 2026-11-08 依 `main` `d6a532f61ec3` 查的快照，開工前先重查 GitHub。

## 現況
Python 參考實作的品質閘門：可執行規格、覆蓋率與 mutation 門檻、架構契約、有界 agent loop policy，以及把「找出 repo 自己的 gate 並執行、保存證據」抽出來的 Cursor 全域 stop hook（`docs/cursor-global-governance.md:1-3`）。2026-11-08 查：open issue／PR 0、Dependabot 與 code scanning open 0，`main` `d6a532f` 上 CI、Dependency freshness、CodeQL 最近一次皆 success（11-02 push），從未發 release（2026-11-08 `gh release list -R SanHsien/ai-quality-gates` 無輸出）。repo 健康；2026-11-02 已實作 Cursor gate 的逾時結果只留證據、下次評估重跑（見 `docs/decisions.md`）；Full 本機各階段通過，本機缺 WSL 發行版所以 Mutation 在本機未跑；改以 Linux CI 驗收：2026-11-08 `gh run view 41476194274` 顯示 `main` `d6a532f`（2026-11-02，含逾時結果修正 `c3d42ab`）的 CI 三個 job 皆 success，其中 `Mutation gate / Python 3.12`（`bash tools/mutation_check.sh`）success，所以 mutation 門檻在這次變更上已驗證，不需要本機 WSL。2026-11-02 已在系統暫存 venv 實測 PyPI 最新版並完成兩組依賴複審，維持宣告下限與鎖檔；另處理 hatchling、pytest 的新鮮度提醒，七筆 deferral 的下次複審日為 2026-12-02（或 PyPI 超過 `deferredLatest` 時），實測與限制見 `docs/decisions.md`。

## 近期：可以直接動手
| 項目 | 為什麼 | 驗收方式 | 建議執行者 | 證據 |
| --- | --- | --- | --- | --- |
| （目前沒有；Mutation 驗收已由 Linux CI 完成，見現況） | 下一輪從中期表挑條件已成立者；複審日 2026-12-02 | — | — | `.github/workflows/ci.yml:70-93`；`gh run view 41476194274` |

## 中期：等條件成立再做
| 項目 | 觸發條件 | 驗收方式 | 建議執行者 | 證據 |
| --- | --- | --- | --- | --- |
| 複審 7 筆依賴延後（import-linter、mutmut、mypy、ruff、coverage、hatchling、pytest） | `.github/dependency-deferrals.json` 的 `revisit` 日（2026-12-02）到期，或 Dependency freshness 因 PyPI 超過 `deferredLatest` 而提醒；`revisit` 不會自動觸發任何檢查，只靠這一列追 | 升級的話以下限版本跑完整 gate、`uv lock --check` 綠（mutmut 另需 Linux CI 的 mutation job 綠）；不升就更新 deferral 的 `deferredLatest`、`reviewed`、`revisit` 與理由 | Codex | `.github/dependency-deferrals.json`；`docs/decisions.md` |
| 啟用排程化的 loop（`loop-policy.toml` `enabled = true`） | 一次手動 maker → checker → state → stop 全路徑實跑成功，且 `loop_runner` 兩項取捨已落地（見 `docs/decisions.md` 2026-10-30） | 手動實跑紀錄（指令與輸出）寫進 `docs/loop-engineering.md`；`tools/check_loop_policy.py` 綠 | 維護者 | `docs/decisions.md:15-17`；`loop-policy.toml` |

## 刻意不做
| 不做什麼 | 理由 | 什麼情況下重新考慮 |
| --- | --- | --- |
| 在本 repo 加第二個路由器或常駐用量採集 | 派工與成本合約歸 agent-advisor（`docs/model-cost-contract.md:3-4`） | agent-advisor 停止維護 |
| 讓 Cursor stop hook 攔截危險指令或無證據完成宣稱 | 動作攔截歸 harness-guard；本 repo 的 hook 只跑 repo 自己宣告的品質 gate 並保存證據 | harness-guard 不再支援 Cursor |
| 把 95% coverage、mutation、complexity 門檻原樣套到其他技術棧的 repo | 那是 Python 參考實作；跨技術棧只抽「找出並執行 repo 自己的 gate」（`docs/cursor-global-governance.md:3`） | 某技術棧有等價且可 fail-closed 的工具鏈 |
| 為了讓新鮮度檢查變綠而直接提高依賴下限 | 下限相容性未獨立測試前，提高下限等於宣稱沒驗過的事 | 以下限版本實跑完整 gate 通過後 |

## 維護方式
自有 repo，直推 main。依賴由 Dependabot（pip、uv、github-actions）與每週 Dependency freshness 追蹤，延後決定寫 `.github/dependency-deferrals.json` 並附複審日。合併前跑 `tools\dev_check.ps1`（Quick／Full），動到核心規則或測試策略才加跑 Mutation。`quality-loop` skill 以本 repo `.agents/skills/quality-loop/` 為 Cursor 安裝來源；agent-assets 那份分岔版的歸屬由 agent-assets 路線圖處理。
