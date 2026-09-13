# 安全政策

## 支援版本

目前只維護 `main`。

## 回報弱點

請使用 GitHub 的 private vulnerability reporting；不要在公開 Issue 貼出可利用細節、憑證或私人資料。

## 自動化邊界

CI 執行 CodeQL 與 pip-audit，但掃描通過不代表不存在未知弱點。涉及認證、權限、金流、個資、資料刪除或外部輸入時，仍需額外威脅建模與人工安全審查。
