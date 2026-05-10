# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案概述

Hyper-V 虛擬化管理儀表板（HVM）。監控多台 Hyper-V 宿主機與其上的 VM，涵蓋資源、快照合規、備份/HA、資安事件四個面向。部署在獨立管理 VM，透過 WinRM 遠端查詢各宿主機。

---

## 啟動與執行

```bash
# 後端 API（從 backend/ 目錄執行）
cd backend
cp .env.example .env        # 首次：填入 WINRM_USER / WINRM_PASSWORD / HV_HOSTS
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 資料收集排程（獨立程序，需 .env 設定 HV_HOSTS）
python -m collector.scheduler

# WinRM 連線測試（驗證能否連上宿主機）
python test_winrm.py        # 需先手動建立，參考 docs/winrm-test-guide.md
```

FastAPI 自動互動文件：`http://localhost:8000/docs`
Dashboard 前端（由 FastAPI 靜態服務）：`http://localhost:8000/`

---

## 架構

### 資料流

```
Hyper-V 宿主機
  └─ WinRM ──▶ collector/ ──▶ SQLite (hv_metrics.db)
                                      │
                              FastAPI routers ──▶ 前端 fetch
```

### 後端（`backend/`）

- **`main.py`**：FastAPI app 進入點，掛載 6 個 router，同時靜態服務 `hv-dashboard/` 前端
- **`database.py`**：SQLAlchemy engine + `SessionLocal` + `get_db()` dependency。`DATABASE_URL` 預設為 SQLite，改一行 `.env` 即可切換 PostgreSQL
- **`models.py`**：8 張資料表。`Host` → `VM` 為一對多；`VM` → `VMMetric / VMSnapshot / VMReplication / BackupJob` 各為一對多；`SecurityEvent` 與 `AlertRule` 無 FK
- **`schemas.py`**：Pydantic response model，每個頁面對應一組 `*Response`
- **`routers/`**：6 個 router，前綴 `/api/<name>`。**目前除 `alerts` 外均回傳 hardcoded mock data**，下一步要改為查 DB
- **`collector/`**：
  - `winrm_client.py`：WinRM 連線封裝，所有 stdout 以 `cp950` 解碼（繁體中文 Windows Server）
  - `vm_collector.py`：`Get-VM` + `Get-Counter`，寫入 `host_metrics` / `vm_metrics`
  - `snapshot_collector.py`：`Get-VMSnapshot`，寫入 `vm_snapshots`（去重）
  - `replication_collector.py`：`Get-VMReplication`，寫入 `vm_replication`
  - `event_collector.py`：Windows Event Log（4624/4625/4728/4732/4740），寫入 `security_events`（去重）
  - `scheduler.py`：APScheduler，vm_metrics 每 15 分鐘、security_events 每 5 分鐘

### 前端（`hv-dashboard/`）

無 build 步驟。React 18 透過 CDN 載入，Babel Standalone 處理 JSX，直接在瀏覽器執行。

- **`HV Dashboard.html`**：入口，依序載入所有 JSX，`App` 元件管理頁面路由（state-based，非 URL routing）
- **`hv-components.jsx`**：共用元件（`Sidebar`、`Topbar`、`Card`、`Metric`、`Sparkline` 等）與 `useFetch` hook。`API_BASE` 預設為空字串（同源），跨域時在 HTML 設定 `window.HVM_API_BASE`
- **`hv-page-*.jsx`**：各頁面元件，透過 `useFetch` 從對應 API endpoint 取資料，有 loading / error 狀態
- **`hv-icons.jsx`**：SVG icon 元件庫

---

## 重要設計慣例

### VM 名稱大小寫正規化
PowerShell `Get-VM` 回傳大寫，`Get-Counter` 路徑為小寫。所有寫入 DB 的 `vm.name` 統一以 `.upper()` 正規化，查詢時同樣 `.upper()` 比對。

### 快照合規規則
- `VM.is_sql = True`：有任何快照即為嚴重違規
- 其他 VM：快照 `age_days > 7` 為違規，`3–7` 天為警告，`≤ 3` 天為合規

### 嚴重度枚舉
全系統統一使用 `err` / `warn` / `ok`（非 `error` / `warning` / `success`），前端 CSS class 也對應此三值。

### mock data → DB 遷移路徑
`routers/alerts.py` 已實作真實 DB 讀寫，可作為其他 router 改寫時的參考範本。其餘 5 個 router 各有一個 `_mock_*()` 函式，改寫時以 SQLAlchemy query 替換該函式回傳值即可。

---

## 環境變數（`backend/.env`）

| 變數 | 說明 |
|---|---|
| `DATABASE_URL` | 預設 `sqlite:///./hv_metrics.db`，可改為 PostgreSQL DSN |
| `WINRM_USER` | 宿主機管理員帳號 |
| `WINRM_PASSWORD` | 宿主機管理員密碼 |
| `HV_HOSTS` | 逗號分隔的宿主機 IP，如 `192.168.1.101,192.168.1.102` |
| `SMTP_*` | 告警 Email 設定（尚未實作） |

---

## 當前開發狀態

| 模組 | 狀態 |
|---|---|
| 前端 6 頁面 | ✅ 完成，接 API |
| `routers/alerts` | ✅ 真實 DB 讀寫 |
| `routers/` 其餘 5 個 | ⏳ 回傳 mock data，待改為查 DB |
| `collector/` 各模組 | ⏳ 骨架完成，待對真實宿主機測試 |
| 告警規則引擎（Email 通知） | ❌ 尚未實作 |
| Veeam backup_collector | ❌ 尚未實作（待採購確認） |
