# 文章與原始脈絡

## 查證範圍

本專案於 2026-08-22 查閱以下資料：

1. Robert C. Martin 的 [X 原始貼文](https://x.com/unclebobmartin/status/2080257779395154409)：主張不逐行閱讀 agent 產生的程式碼，改以單元測試、Gherkin、QA、品質指標、mutation 與 coverage 等強約束建立信心。
2. Martin 的 [測試負載反思貼文](https://x.com/unclebobmartin/status/2072736888478175413)：提醒可以自動化很多測試，不代表每次變更都應無差別執行全部層級。
3. Martin 2016 年的 [Mutation Testing](https://blog.cleancoder.com/uncle-bob/2016/06/10/MutationTesting.html)：說明 coverage 只代表執行過，mutation testing 用語意變更檢查測試是否真的會失敗。
4. [INSIDE 報導](https://www.inside.com.tw/article/41914-clean-code-author-uncle-bob-says-he-no-longer-reads-ai-written-code)：整理 2026 年討論與正反意見。
5. [延伸脈絡整理](https://www.explainx.ai/blog/uncle-bob-ai-coding-gauntlet-tests-not-reviews-july-2026)：記錄 Martin 會依 criticality 檢視 Gherkin/QA，並定期進行手動測試。這是二手來源，因此不把其轉述當成獨立的一級證據。

X 頁面可能要求登入或限制自動擷取；本文件保留直接 URL，並用本人長期公開文章交叉檢查 mutation/coverage 的核心主張。

## 從新聞摘要修正出的重點

- 「不讀 code」不是「不負責」：人類判斷移到需求、驗收規格、QA 程序、門檻與發布決策。
- coverage 不是品質分數：它適合找未執行區域，不能證明 assertion 正確。
- mutation 是測試的測試：survivor 代表現有測試未察覺某個工具產生的語意變更。
- 風險決定 gate 深度：小變更可用快速 gate，高風險核心規則才追加完整 mutation。
- 架構必須另設 contract：行為測試通過，仍可能產生錯誤依賴或過大模組。

## 本 repo 的立場

自動化應先提供可重現的失敗證據，再縮小人工判斷範圍。它不取消 code review，也不替代資安、法遵、領域專家或事故責任；團隊可依 criticality 決定人工 review 的深度。
