# Loop Engineering：從品質關卡到有界自治

## 來源層級

本文件於 2026-08-22 查證並區分原始材料與整理文章：

1. Boris Cherny 的一級來源是 WorkOS 主辦的 [Acquired Unplugged 完整訪談影片](https://www.youtube.com/watch?v=RkQQ7WEor7w)，不是 Cherny 署名文章。他在訪談中說明工作方式已從直接提示轉向編排自動化 loops。
2. [WorkOS 訪談整理](https://workos.com/blog/boris-cherny-claude-code-acquired-interview-takeaways)由活動主辦方撰寫，是接近原始事件的二級來源。
3. Peter Steinberger 於 2026-06-07 的 [X 原始貼文](https://x.com/steipete/status/2063697162748260627)提出「設計 prompts agent 的 loops」。查閱其[個人網站](https://steipete.me/)未找到同月長文，因此不把後續媒體解讀誤稱為他的原始文章；[OpenClaw `/loop` 文件](https://docs.openclaw.ai/tools/slash-commands)則可驗證 owner-only、固定節奏與停止命令等產品邊界。
4. Addy Osmani 於 2026-06-07 發表的 [Loop Engineering](https://addyosmani.com/blog/loop-engineering/)是命名與六項元件的作者原文；同月的 [Agentic Code Review](https://addyosmani.com/blog/agentic-code-review/)把瓶頸定位在信任與驗證，[The New Software Lifecycle](https://addyosmani.com/blog/new-sdlc-vibe-coding/)及其共同撰寫的 [Google 白皮書](https://www.kaggle.com/whitepaper-the-new-SDLC-with-vibe-coding)則把 agent 表述為 model 加 harness。
5. arXiv 論文 [Stop Hand-Holding Your Coding Agent](https://arxiv.org/abs/2607.00038)把 loop 定義為包含 trigger、goal、verification、stopping rule 與 memory 的有界工程 artifact，並指出四層能力是互補而非互相淘汰。
6. 中文脈絡來自使用者提供的[文章](https://www.woshipm.com/ai/6414092.html)與摘要、2026-06-14 的[「Harness 長出的外循環」分析](https://www.woshipm.com/share/6413154.html)，以及 2026-07-11 的[實作型深讀](https://www.woshipm.com/ai/6427806.html)；另以人人都是產品經理的[工程躍遷整理](https://www.woshipm.com/ai/6414536.html)及[Agent 全流程整理](https://www.woshipm.com/ai/6415411.html)交叉檢查。
7. 數位時代於 2026-06-15 發布的[迴圈工程介紹](https://www.bnext.com.tw/article/91246/loop-engineering-from-prompting-to-designing-ai-coding-loops)補充五階段執行模型、最小可行迴圈與營運成本觀點。該頁明示「本文初稿為 AI 編撰，整理．編輯／李先泰」，因此列為二級整理，技術與人物主張仍回查前述原始來源。

因此，本 repo 不把「Prompt 已死」當成事實。Addy 把 loop 描述為 harness 上方的控制層，中文文章則稱它是 harness 長出的外循環；兩者共同指出的工程關係是「包覆與反饋」，不是淘汰。Prompt、Context、Harness、Loop 由內向外疊加，外層仍依賴內層的明確指令、乾淨脈絡與可靠工具。

## 2026 年 6 月公開論述的共同點與差異

- Steinberger 的貼文是方向性主張，不是完整規格；OpenClaw 文件補上 owner-only、cadence 與可停止等實際控制面。
- 中文文章寫 Osmani 在「第二天」發文，但 Steinberger 的 X 貼文與 Osmani 頁面都標示 2026-06-07；這可能受時區或發布順序影響，本 repo 不據此推定精確先後。
- Osmani 提出 automations、worktrees、skills、connectors、sub-agents 加持久 memory，並反覆提醒 token 成本、自我評分偏誤、comprehension debt 與 cognitive surrender。
- Osmani 的 Google SDLC 脈絡強調 model 只是 agent 的一部分，rules、tools/MCP、sandbox、orchestration、hooks、tests 與 observability 都屬 harness。
- 中文文章「Harness 長出的外循環」有助於避免把 Loop Engineering 誤解為全新技術層；它是二級分析，日期、人物說法與產品能力仍以上述原始來源為準。
- 7 月的實作型文章補上 `PASS`／`FAIL`／`NEEDS_HUMAN`、最多兩次重試、先手動跑通再排程與最小 backlog 等有用做法。本 repo 採納這些控制，但不採納把 `.env` 複製進 worktree、預先給廣泛 GitHub 寫入權或驗證後自動開 PR 的示例；秘密與外部寫入的 blast radius 必須另行縮限。

## 五階段與六元件不是同一件事

數位時代整理的 `Discover → Plan → Execute → Verify → Iterate` 描述一次 loop 的執行狀態；六元件描述讓這個狀態機能可靠運作的基礎設施。驗證通過才可結束，失敗則帶著具體證據進入 Iterate，再回到必要的探索或規劃，不是從頭盲目重跑。

它提出的最小可行迴圈是 automation、skill、state 與 gate。本 repo 已具備後三者，automation 則刻意維持停用；必須先用一次人工執行證明 maker、checker、state 與 stop path 完整，才值得排程。

「每個被採納修改的成本」比總 token 數更接近實際價值，可以在未來 runner 實作後作為營運指標。但文章提到的 50% 採納率是經驗法則，不是跨專案通用的正確性門檻，本 repo 不將它寫入 fail-closed policy。

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
