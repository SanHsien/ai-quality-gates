# 設計決策

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
