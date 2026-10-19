# 跨 agent 成本證據

Codex、Claude 原生／3P、Cursor、Antigravity、Hermes 的派工合約由 agent-advisor 管理。
本 repo 繼續負責品質、獨立 checker 與有界 loop，不加入第二個路由器或常駐採集工具。

任務成本包含主模型、worker、顧問、reviewer、失敗與重試；用量來源及 provider 原始欄位須保留。
美元估算需費率來源及日期；訂閱額度不是 API 費用。缺失欄位標 unknown。
每件合格交付成本 = 所有嘗試成本 / 通過驗收件數。不可用單次呼叫價格或官方 benchmark 替代本機效果。

驗證證據可沿用的必要條件：命令與輸出可查、完整工作樹 hash、依賴及環境一致、freshness 有效。
獨立 checker 與 require_machine_evidence 的 current-HEAD full gate 不可省略。
不要修改現有預算或降低品質門檻來證明省費。
