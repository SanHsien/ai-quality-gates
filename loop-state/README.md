# Loop runtime state

自動化 loop 可在此目錄建立未追蹤的 `state.json`，只保存可續跑的最小狀態：

```json
{
  "task": "bounded task identifier",
  "iteration": 1,
  "changed_paths": [],
  "last_failure": null,
  "evidence_paths": [],
  "remaining_tokens": 100000,
  "next_action": "run focused test"
}
```

不要保存秘密、cookie、token、完整 prompt、完整工具輸出或個人資料。終止後可保留不含敏感資訊的 evidence pointer；runtime `state.json` 不提交 Git。
