# Loop Engineering：從品質關卡到有界自治

## 核心模型

Loop Engineering 把一次性提示提升為可重複、可觀測且有停止條件的工作系統。Prompt、Context、Harness 與 Loop 是由內向外疊加的互補層：外層 loop 仍依賴明確指令、乾淨脈絡、可靠工具與可判定的驗收 oracle。

一個可治理的 loop 至少包含 trigger、goal、state、verification、stopping rule 與最小持久記憶。Agent 只是 harness 的一部分；rules、tools/MCP、sandbox、orchestration、hooks、tests 與 observability 共同決定它能否安全運作。

主要風險包括 token 成本失控、自我評分偏誤、反覆嘗試卻沒有進展、理解債，以及把判斷責任交給自動化。因而 loop 必須預設有界、可中止，並讓不可逆或高風險操作回到人工核准。

## 五階段與六元件不是同一件事

`Discover → Plan → Execute → Verify → Iterate` 描述一次 loop 的執行狀態；六元件描述讓這個狀態機能可靠運作的基礎設施。驗證通過才可結束，失敗則帶著具體證據進入 Iterate，再回到必要的探索或規劃，不是從頭盲目重跑。

最小可行迴圈由 automation、skill、state 與 gate 組成。本 repo 已具備後三者，automation 則刻意維持停用；必須先用一次人工執行證明 maker、checker、state 與 stop path 完整，才值得排程。

「每個被採納修改的成本」比總 token 數更接近實際價值，可以在未來 runner 實作後作為營運指標。採納率與 token 用量是成本訊號，不是跨專案通用的正確性門檻，因此不寫入 fail-closed policy。

## 六項基礎設施如何落地

| 元件 | 本 repo 的實作 | 邊界 |
| --- | --- | --- |
| Trigger | 人工啟動、CI push/PR、`workflow_dispatch` | 不預設排程，不自行擴大任務 |
| Worktree / Sandbox | `loop-policy.toml` 強制獨立工作區，最多一個平行 worktree | 不在未隔離環境跑長迴圈 |
| Skill library | [quality-loop skill](../.agents/skills/quality-loop/SKILL.md) | 只保存決策規則，不塞入完整歷史 |
| Connector / MCP | 預設 read-only、明確憑證才可用 | 高風險外部寫入停下交人 |
| Maker / Checker | 政策強制獨立 verifier，測試與 gate 提供客觀反饋 | 同一 agent 的自評不能作為通過證據 |
| State / Memory | `loop-state/state.json` 保存最小續跑狀態 | runtime state 不進 Git，不得含秘密 |

`tools/check_loop_policy.py` 會 fail closed：任何無界迭代、缺少 token/time budget、自我驗證、直接推送、auto-merge、越界 state path 或缺少高風險人工核准類別都會使 Quick/Full gate 失敗。

## 適用判準

只有同時接近下列條件時才適合啟動 loop：

- 工作會重複出現，值得攤提建立 loop 的成本。
- 成功可由測試、型別、lint、行為規格或其他確定性證據判定。
- 工具可安全且可靠地讀寫目標範圍。
- 時間、token、迭代次數與停止狀態均已設定硬上限。

模糊產品方向、一次性研究、缺乏 oracle 的主觀決策，以及涉及高風險外部寫入的工作，應維持人在迴圈內。

## 反饋、停止與責任

最小循環是 `Discover → Plan → Execute → Verify → Iterate`；每個階段都更新精簡 state，Verify 必須由獨立 checker 依機械證據判斷。以下任一條件立即停止：

- 驗收條件全數通過；
- 達到 iteration、elapsed time 或 token 上限；
- 同一失敗重複兩次，顯示可能 thrashing；
- checker 找到 policy violation 或無法建立機械證據；
- 進入需要人工核准的風險類別。

Checker 的結果應限制為 `PASS`、`FAIL` 或 `NEEDS_HUMAN`，並附自己重跑的證據。啟用 scheduler 前，先人工跑通一次完整鏈路；這也是 `loop.enabled = false` 的實際含義。

Maker 宣稱「完成」不具終止效力。只有 checker 的客觀 gate 能把 state 設為 `complete`，避免 Ralph Wiggum 式過早完成訊號讓半成品靜默退出。

這些限制降低 context drift、token 失控、reward hacking 與 comprehension debt，但不消除責任。人仍負責需求真偽、禁止事項、風險分類、驗收 oracle 與最終發布。

## 刻意未自動化

本 repo 目前只提供可執行政策與品質關卡，不提供無人值守 runner，也不自動建立 connector、提交、推送、合併或部署。先用人工觸發證明工作流穩定，再考慮加入 scheduler；`loop.enabled = false` 是有意的安全預設。
