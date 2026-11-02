# 設計決策

## 2026-11-02：依賴複審維持下限與鎖檔

開工時工作樹乾淨，HEAD 為 `c3d42ab5c93e944d8898049f97dca4a83f0dace1`。即時 PyPI 查詢確認 mutmut 3.8.1、mypy 2.4.1、ruff 0.17.3 超過既有 `deferredLatest`，兩組中期複審項目的觸發條件成立；import-linter 仍為 2.15、coverage 仍為 7.17.0。strict 檢查另指出 hatchling 1.33.0、pytest 9.2.0，合併實測後記錄延後理由，沒有為了綠燈提高宣告下限。

實測環境為 Windows、Python 3.12.14，venv 與完整輸出位於系統暫存目錄 `$env:TEMP/aqg-dependency-review-20261102`，不加入版本控制。先以 `uv sync --frozen --python 3.12` 建立暫存 venv（`UV_PROJECT_ENVIRONMENT` 指向該處），再用 `uv pip install --python <venv>/Scripts/python.exe --upgrade import-linter mutmut mypy ruff coverage hatchling pytest` 安裝最新版，兩步 exit 0；後續直接呼叫該 venv 的執行檔，避免 `uv run` 自動還原鎖版。

| 暫存環境命令（以下 python 均指該 venv） | Exit code | 結尾證據 |
| --- | --- | --- |
| `python -m ruff format --check .` | 0 | 58 files already formatted |
| `python -m ruff check .` | 0 | All checks passed! |
| `python -m mypy src tools` | 0 | Success: no issues found in 21 source files |
| `<venv>/Scripts/lint-imports.exe` | 0 | Contracts: 1 kept, 0 broken. |
| `python -m pytest -q --cov=quality_gate_demo --cov-branch --cov-report=term-missing --cov-report=json:<temp>/latest-coverage.json --junitxml=<temp>/latest-junit.xml` | 0 | 125 passed；coverage 97.98%，門檻 95% |
| `<venv>/Scripts/behave.exe --no-capture` | 0 | 3 scenarios passed, 0 failed, 0 skipped；15 steps passed |
| `python tools/qa_smoke.py` | 0 | QA SMOKE GREEN: example order total=5130 |
| `python -m hatchling build -d <temp>/dist` | 0 | wheel 與 sdist 產物皆已建立 |

決定：import-linter、mypy 的 Windows 最新版檢查通過，但尚未驗證完整 Python／OS 矩陣，保留現行 lock，待整批鎖檔升級時驗證。mutmut 3.8.1 僅證明可安裝與搭配其他工具跑 lint／測試，不能據此宣稱 mutation 相容；實際呼叫 `wsl.exe --cd <repo> bash -lc "bash tools/mutation_check.sh"`（Windows gate 的同一 Mutation 階段）回傳 -1，本機沒有 WSL 發行版，保留 lock 3.7.0。ruff、coverage 未以下限版本獨立實跑完整 gate，因此維持下限；hatchling、pytest 也先保留宣告及鎖檔，等完整矩陣驗證。七筆 deferral 統一記錄 `reviewed = 2026-11-02`、`revisit = 2026-12-02`，版本精度沿用既有條目（import-linter 兩段，其餘三段）。

鎖定環境驗證：`uv lock --check` exit 0；`pwsh -NoProfile -File tools/dev_check.ps1` exit 0，結尾 `FULL GATE GREEN`，125 tests、0 failures/errors/skipped、coverage 97.98%，`artifacts/quality-summary.json` 的 `profile=full`、`passed=true`、所有 gates=true。Full 在文件與 deferral 更新前取得；更新後只補跑受影響的文件與新鮮度檢查，不重複已通過的高成本套件。Mutation 的 Full 前置階段沿用此證據，不再透過 `-Mutation` 重跑整套；WSL 階段未完成，原有路線圖待驗收列保留。

本次沒有修改程式行為或修 bug，無需新增先紅後綠的回歸測試；依賴新鮮度的實際基線為 `python tools/check_dependency_freshness.py --strict --output <temp>/freshness-before.md` exit 1，更新 deferral 後以相同 strict 檢查 exit 0；`uv run python tools/check_docs.py` exit 0（DOCS GREEN: 20 Markdown files checked），`uv run pytest -q tests/tools/test_check_dependency_freshness.py` exit 0（8 passed），`git diff --check` exit 0。完整輸出分別保存在暫存目錄的 `full.log`、`latest-*.log`、`mutation.log` 與 `freshness-*.log`。後續工作只由 `ROADMAP.md` 追蹤。

## 2026-11-02：Cursor gate 逾時證據不重用為快取

exit 124 表示驗證未完成，不能作為同一 fingerprint 永久失敗的依據。採取保守且可回復的做法：仍將逾時的 failed 狀態、exit code 與輸出寫入原有 state.json，但 evaluate 遇到 124 紀錄時重跑 gate，不論紀錄是新版或舊版寫入。成功與一般非零失敗維持原本快取行為。

不採短效期，避免引入時間判斷、時鐘偏移與額外設定；不刪除既有證據、不變更 state schema 或信任政策。代價是持續逾時時，每次評估都會再付出一次 gate 的時間成本；每次評估最多執行一次，仍沿用既有 timeout 與 stop_hook_active 防遞迴邊界，不增加背景或同次自動重試。恢復成功後，同一 fingerprint 即恢復快取。重看條件：若持續逾時讓每次 stop hook 的成本不可接受，或 gate 改為可續跑或分批，再評估短效期快取或逾時專用狀態。

## 2026-08-22：使用 Python 與 uv

Python 的 pytest、Behave、coverage、Radon、Import Linter 與 mutmut 能覆蓋行為、結構與測試有效性等主要關卡。uv 提供 lockfile、跨平台安裝與可重現命令，Windows 使用 `.venv`，Linux/WSL 使用獨立環境，避免交叉污染。

## 2026-08-22：保留分層 gate

驗證深度應依 criticality 調整。專案因此分成 Quick、Full、Mutation，不把最昂貴的 mutation 放進每次本機迭代。

## 2026-08-22：量化指標採 fail-closed，但不宣稱證明正確

coverage、complexity、module size 與 mutation 都有明確門檻，缺少報告或 total 為零時視為失敗。文件同時保留各指標的盲點，避免 Goodhart's law 式追逐分數。

## 2026-08-22：Loop 預設停用，政策先於 runner

Loop Engineering 的價值在可持續的反饋與狀態，不在無限重試。本 repo 先交付可測試的 `loop-policy.toml` 與 checker，強制 iteration、time、token、隔離、獨立 verifier、人工核准與 terminal states；在尚未以人工觸發證明穩定前，不加入 scheduler 或無人值守 runner。

## 2026-10-30：Loop 重複失敗判定改用穩定特徵，驗證指令納入時間預算

重複失敗（`stop_on_repeated_failure`）判定原本比對輸出末行字串，但測試工具（如 pytest 的 `in 0.52s`、Behave 的 `Took 0min 0.002s`）每次耗時數字浮動，造成連續相同失敗幾乎不觸發；同時時間上限以往僅在迭代間隙檢查，單次驗證指令若卡死會無限超時。

取捨與實作：
1. **穩定特徵比對**：優先提取失敗案例名稱集合（`FAILED ` 項目）排序組合；若無則正規化末行摘要，清除時間戳記與耗時數字（如 `in Xs`、`Took Xmin Xs`），避免計時微小擾動破壞重複判斷。`state.last_failure` 仍保留原始末行摘要供維護者查閱。
2. **驗證指令逾時約束**：驗證階段依 `max_elapsed_minutes` 計算當前剩餘秒數，作為驗證指令執行的 timeout 上限。逾時指令由子行程機制終止，並直接將狀態收斂至 `budget_exhausted`（`stop_time_limit`），確保單次驗證不突破整體時間邊界。
3. **逾時真的終止**：`tools/loop_verifier.py` 以 `Popen(shell=True)` 啟動驗證指令並放進新的行程群組（Windows `CREATE_NEW_PROCESS_GROUP`、POSIX `start_new_session`）。逾時後 Windows 用 `taskkill /F /T /PID`、POSIX 用 `os.killpg(SIGKILL)` 殺整棵樹（`shell=True` 只殺 shell 本身，孫行程會讓 `communicate()` 無限等待），再限時 5 秒回收輸出並重新拋出 `TimeoutExpired`。
4. **失敗輸出合併 stdout 與 stderr**：驗證失敗時回傳 `stdout` 接 `stderr`。測試的 `FAILED` 行在 stdout，`dev_check.ps1` 的 `throw` 在 stderr，只取其一會丟掉另一邊的證據。
5. **特徵比對細節**：`FAILED`／`ERROR` 行取 ` - ` 之前的測試 id（訊息可能含浮動內容）；耗時必須帶單位才算（`in 0.52s`、`Took 0min`，`Found 2 errors in 5 files` 不受影響），pytest 的 `(0:01:03)` 一併去除；清空後退回 `exit <code>`，不退回原文。

已知限制：unittest 的 `FAILED (failures=1)` 沒有測試 id，特徵只剩該字串，因此不同測試的失敗會被視為相同失敗；用 pytest 作驗證指令時不受影響。另外，`timeout after 30s` 與 `timeout after 60s` 會判為相同（末行 fallback 把帶單位的數字當耗時），後果是提早停下來給人看，方向安全。
