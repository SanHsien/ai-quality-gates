# Cursor 全域治理安裝

`ai-quality-gates` 的 95% coverage、mutation、complexity 與 Import Linter 契約是 Python 參考實作，不能原樣套到每個 repository。本整合只抽出跨技術棧都成立的治理層：**找出 repo 自己的 gate、執行、保存證據、失敗不得宣稱完成**。

## 安裝

先預覽，不寫入：

```powershell
python tools/install_cursor_global.py --dry-run --trusted-github-owner SanHsien
```

正式安裝：

```powershell
python tools/install_cursor_global.py --trusted-github-owner SanHsien
```

安裝器會：

1. 複製動態 router 到 `~/.cursor/hooks/ai_quality_gate.py`，核心模組放在同一目錄。
2. 合併一個 `stop` hook 進 `~/.cursor/hooks.json`，不覆蓋其他 hook。
3. 安裝 always-apply rule `~/.cursor/rules/ai-quality-governance.mdc`。
4. 安裝 `quality-loop` 到 `~/.cursor/skills/quality-loop/`。
5. 修改既有 `hooks.json` 或 `trust.json` 前備份到 `~/.cursor/backups/`。
6. 將明確指定的 GitHub owner 合併到使用者層級 `~/.cursor/governance/trust.json`；未指定 owner 時採 fail-closed，repo-native command 不會自動執行。

安裝可重跑；內容與註冊都相同時 `changed: false`。

## 現在與未來 repo 如何生效

Router 不維護 repo 白名單。Cursor 每次在 Git repository 結束回合時，從 payload 的 `cwd`／`workspace_roots` 解析目前 repo，因此：

- 現有 repo：下次在 Cursor 開啟時自動納管。
- 未來 repo：clone／init 後第一次在 Cursor 開啟即自動納管。
- 不必在每個 repo 複製 Python 工具或新增設定檔。

自動執行 repo-native command 前另套用使用者層級信任政策：指定 owner 的 GitHub repo 可執行正式 gate；外部 owner、無 origin 或未明確信任的 repo 只以可信的 Git executable 執行 working-tree 與 staged `git diff --check`。本機尚未 push 的新 repo 若要執行 native gate，需先在 `trust.json` 的 `trusted_repositories` 加入其絕對路徑。

同一個 `HEAD + working tree + gate command` 只執行一次；結果快取在 `~/.cursor/governance/state.json`。任何變更都會產生新 fingerprint 並重跑。

## Gate 探測順序

1. 受信任 repo 的 `.ai-quality-gates.json` 明確設定；repo 自己不能藉此自行取得信任。
2. `tools/dev_check.ps1`；只有腳本真的宣告 `$Quick` 才加 `-Quick`。
3. `tools/dev_check.sh`。
4. `scripts/run_tests.sh`。
5. `package.json` 的 `verify`、`check`、`test`，依 lockfile 選 npm／pnpm／yarn／bun。
6. Python、Go、Rust、Maven、Gradle 的保守預設。
7. 都沒有時，對 working tree 與 staged index 執行 universal `git diff --check` baseline；它只證明 diff 沒有 whitespace error，不代表 build／test 通過。

自動執行設為 offline：不准 gate 在背景下載或安裝依賴。缺依賴時應失敗並留下證據，不偷偷改環境。

手動查看探測結果：

```powershell
python "$HOME/.cursor/hooks/ai_quality_gate.py" --discover <repo-path>
```

手動執行一次且略過快取：

```powershell
python "$HOME/.cursor/hooks/ai_quality_gate.py" --check <repo-path>
```

## Repo override

只有探測錯誤或 repo 有正式專用入口時才新增：

```json
{
  "enabled": true,
  "quick": "pwsh -NoProfile -File tools/dev_check.ps1 -Quick",
  "timeout": 180
}
```

`"enabled": false` 可明確退出。不得用 opt-out 隱藏已知紅燈。

## 安全邊界

- Cursor `stop` 不能 veto 已完成回合；失敗會以 `followup_message` 要求 agent 修正。
- Router 不會 auto-merge、push、deploy、刪檔、處理 secrets 或改 repo。
- 不會把 Python 門檻硬灌給 Node／Go／Rust／純文件 repo。
- 沒有 repo-native gate 時只取得 `global-baseline` 證據；不得把它寫成 build／test／coverage 已驗證。
- Full／Mutation 仍由 repo 明確定義並在高風險交付前人工觸發；全域 stop hook只跑 narrow quick gate。

## 回退

1. 從 `~/.cursor/hooks.json` 移除 command 包含 `ai_quality_gate.py` 的 `stop` entry；或還原安裝器回報的 backup。
2. 刪除 `~/.cursor/hooks/ai_quality_gate.py`、`~/.cursor/hooks/cursor_gate_core.py`、`~/.cursor/hooks/cursor_gate_baseline.py`、`~/.cursor/hooks/cursor_gate_git.py`、`~/.cursor/hooks/cursor_gate_trust.py`。
3. 刪除 `~/.cursor/rules/ai-quality-governance.mdc`。
4. 從 `~/.cursor/governance/trust.json` 移除本次加入的 owner；若有其他 owner／path，保留它們，勿整檔刪除。
5. `quality-loop` 若原先已由其他來源安裝，可保留。
6. 重新開啟 Cursor 視窗並檢查 Hooks 輸出。
