# Changelog

本專案遵循 Keep a Changelog 的分類方式。

## [Unreleased]

### Added

- Python 訂單報價示範 domain 與 CLI。
- pytest unit/integration、Gherkin/Behave 與 QA smoke。
- coverage、mutation、complexity、module-size 與 dependency contracts。
- Windows、Linux/WSL 開發入口及 GitHub CI、安全與依賴自動化。
- 每月依賴新鮮度檢查：`tools/check_dependency_freshness.py` 與 `Dependency freshness` workflow，
  比對宣告與 PyPI 現行版；紅燈的兩條出口是 `# freshness-hold:` 與
  `.github/dependency-deferrals.json`，兩者都要寫理由。

### Changed

- 開發依賴下限：coverage 7.15 → 7.16、import-linter 2.13 → 2.14，lock 一起升。依賴新鮮度檢查的兩筆「待審視」；升版後完整閘門仍全綠。

- 開發依賴下限對齊 `uv.lock` 實際鎖定的版本（coverage 7.15、hatchling 1.32、import-linter 2.13、
  mutmut 3.7、mypy 2.3、pip-audit 2.10、pytest 9.1、pytest-cov 7.1、ruff 0.16）。宣告原本停在
  建立當時的舊版，鎖檔卻早已前進——落後的是宣告本身。
- 品質信心、人工責任、指標限制與分層驗證的工程原則。
- Loop Engineering 五階段、六項基礎設施、適用判準與停止規則。
- 有界 `loop-policy.toml`、fail-closed checker、repo-local skill 與 runtime state 契約。
- 實作型 Loop 案例的 tri-state checker、兩次失敗升級人工與「先手動證明再排程」原則。
- 五階段執行模型、過早完成的無聲失敗與採納成本辨析。
