# Hyper-V Monitor（HVM）

Hyper-V 虛擬化環境統一管理儀表板，讓 IT 工程師與管理層透過單一介面掌握環境狀況，無需開啟 PowerShell 或逐一登入主機查詢。

---

## 功能概覽

| 視角 | 內容 |
|---|---|
| **總覽** | 系統健康度、告警事項、各視角燈號摘要 |
| **資源監控** | 實體主機 CPU/RAM/儲存、VM 清單與 7 天趨勢 |
| **快照合規** | 快照存在天數、違規清單、SQL Server VM 特殊規則 |
| **備份 / HA** | 異地複寫狀態與 RPO 達標率（Veeam 整合待實作） |
| **資安監控** | Windows Event Log 異常登入、帳號鎖定、群組異動 |
| **告警設定** | 門檻值調整、啟用/停用規則、Email / Webhook 通知 |

---

## 架構

```
管理 VM（2 vCPU / 4 GB RAM）
├── FastAPI 後端       ← REST API + 靜態服務前端
├── SQLite 資料庫      ← hv_metrics.db
└── Collector 排程     ← 每 5–15 分鐘採樣
        │
        │ WinRM（TCP 5985）
        ▼
Hyper-V 宿主機（KHFACVS01、KHFACVS02 ...）
└── PowerShell 遠端查詢：Get-VM / Get-Counter / Get-VMSnapshot / Event Log
```

**技術棧**

| 層 | 選型 |
|---|---|
| 前端 | React 18（CDN，無 build 步驟）、純 CSS Dark Mode |
| 後端 | Python FastAPI + SQLAlchemy ORM |
| 資料庫 | SQLite（可切換 PostgreSQL，改一行 `.env`） |
| 資料收集 | pywinrm + APScheduler |
| 通知 | smtplib Email + Webhook（`{{$variable}}` 模板） |

---

## 快速開始

### 1. 環境需求

- Python 3.10+
- 管理端可透過 TCP 5985 到達各 Hyper-V 宿主機
- 宿主機已啟用 WinRM（`winrm quickconfig`）

### 2. 安裝

```bash
git clone <repo-url>
cd hyperVmonitor/backend

pip install -r requirements.txt

cp .env.example .env
# 編輯 .env，至少填入以下三項：
#   WINRM_USER=administrator
#   WINRM_PASSWORD=your_password
#   HV_HOSTS=192.168.1.101,192.168.1.102
```

### 3. 啟動 API

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

瀏覽器開啟 `http://<管理機IP>:8000` 即可看到 Dashboard。

API 互動文件：`http://<管理機IP>:8000/docs`

### 4. 啟動資料收集排程

```bash
cd backend
python -m collector.scheduler
```

| 採集項目 | 間隔 |
|---|---|
| VM 指標（CPU / RAM / 網路）| 每 15 分鐘 |
| 快照清單 | 每 15 分鐘 |
| 複寫狀態 | 每 15 分鐘 |
| 安全事件（Event Log）| 每 5 分鐘 |

### 5. WinRM 連線驗證（首次部署）

```bash
cd backend
python test_winrm.py   # 讀取 .env 設定，測試 8 個項目
```

詳細步驟：[docs/winrm-test-guide.md](docs/winrm-test-guide.md)

---

## 設定說明（`backend/.env`）

```env
# ── 資料庫 ──────────────────────────────────────────────
DATABASE_URL=sqlite:///./hv_metrics.db
# 切換 PostgreSQL：DATABASE_URL=postgresql://user:pass@host:5432/hv_monitor

# ── 宿主機連線 ──────────────────────────────────────────
WINRM_USER=administrator
WINRM_PASSWORD=your_password
HV_HOSTS=192.168.1.101,192.168.1.102   # 逗號分隔，支援多台

# ── Email 通知 ───────────────────────────────────────────
SMTP_HOST=mail.company.com
SMTP_PORT=25
SMTP_SENDER_EMAIL=hv-monitor@company.com
SMTP_SENDER_NAME=Hyper-V Monitor
ALERT_EMAIL_IT=it-team@company.com
ALERT_EMAIL_MANAGER=it-manager@company.com
DASHBOARD_URL=http://192.168.1.200:8000

# ── Webhook 推播（可選）──────────────────────────────────
WEBHOOK_ENABLE=false
WEBHOOK_URL=http://internal-api.company.com/webhook
WEBHOOK_TOKEN=your_token
WEBHOOK_BODY_TEMPLATE={"token":"{{$token}}","content":"{{$message}}"}
WEBHOOK_USE_PROXY=false
WEBHOOK_PROXY_URL=
```

### 跨域存取前端

若前端與 API 不在同一個 origin，在 `hv-dashboard/HV Dashboard.html` 的 `<head>` 加入：

```html
<script>window.HVM_API_BASE = 'http://192.168.1.200:8000';</script>
```

---

## 快照合規規則

| 狀態 | 條件 |
|---|---|
| 🔴 嚴重違規 | SQL Server VM（`is_sql=True`）有任何快照 |
| 🔴 違規 | 快照存在 > 7 天 |
| 🟡 警告 | 快照存在 3–7 天 |
| 🟢 合規 | 無快照，或快照存在 ≤ 3 天 |

SQL Server VM 需在 VM 初次同步後，以 API 或直接更新 DB 設定 `vm.is_sql = 1`。

---

## VM 標記說明

| 欄位 | 說明 | 設定方式 |
|---|---|---|
| `vm.is_sql` | SQL Server VM（快照即違規）| 手動更新 DB |
| `vm.tier` | `Tier1`（RPO ≤4hr）/ `Tier2`（RPO ≤24hr）| 手動更新 DB |

```sql
-- 範例：標記 KHTWXDB 為 SQL Server Tier1 VM
UPDATE vms SET is_sql=1, tier='Tier1' WHERE name='KHTWXDB';
```

---

## 開發狀態

| 模組 | 狀態 |
|---|---|
| 前端 6 頁面 | ✅ 完成，接真實 API |
| 全部 6 個 API endpoint | ✅ 真實 DB 查詢 |
| WinRM Collector（VM / 快照 / 複寫 / 事件）| ✅ 完成，宿主機測試通過 |
| Email / Webhook 通知服務 | ✅ 模組完成，待接告警引擎 |
| 告警規則引擎（閾值觸發通知）| ⏳ 待實作 |
| Veeam 備份 Collector | ❌ 待採購確認後實作 |

---

## 目錄結構

```
hyperVmonitor/
├── backend/
│   ├── main.py                    # FastAPI 進入點，掛載 6 個 router
│   ├── database.py                # SQLAlchemy engine + Settings（讀 .env）
│   ├── models.py                  # 9 張資料表 ORM 定義
│   ├── schemas.py                 # Pydantic response schemas
│   ├── requirements.txt
│   ├── .env.example
│   ├── test_winrm.py              # WinRM 連線測試腳本（讀 .env）
│   ├── routers/
│   │   ├── overview.py            # GET /api/overview
│   │   ├── resources.py           # GET /api/resources, /api/resources/vms/{name}
│   │   ├── snapshots.py           # GET /api/snapshots
│   │   ├── backup.py              # GET /api/backup
│   │   ├── security.py            # GET /api/security
│   │   └── alerts.py              # GET/PATCH /api/alerts
│   ├── collector/
│   │   ├── winrm_client.py        # WinRM 連線封裝（cp950 解碼）
│   │   ├── vm_collector.py        # Get-VM + Get-Counter（CPU 全 VP 平均）
│   │   ├── snapshot_collector.py  # Get-VMSnapshot
│   │   ├── replication_collector.py # Get-VMReplication
│   │   ├── event_collector.py     # Windows Event Log（4624/4625/4728/4732/4740）
│   │   ├── scheduler.py           # APScheduler（15min / 5min）
│   │   └── utils.py               # parse_ps_datetime（7 位小數秒處理）
│   └── notifier/
│       ├── email_service.py       # SMTP 郵件服務
│       ├── webhook_service.py     # Webhook 推播（{{$variable}} 模板）
│       └── templates.py           # HTML 郵件模板（即時告警 / 彙整 / 日報）
├── hv-dashboard/                  # 前端（無 build 步驟，CDN React）
│   ├── HV Dashboard.html          # 入口
│   ├── hv-components.jsx          # 共用元件 + useFetch hook
│   ├── hv-page-overview.jsx
│   ├── hv-page-resources.jsx
│   ├── hv-page-snapshots.jsx
│   ├── hv-page-backup.jsx
│   ├── hv-page-security.jsx
│   ├── hv-page-alerts.jsx
│   └── hv-icons.jsx
└── docs/
    └── winrm-test-guide.md        # WinRM 連線測試指南（含排錯）
```
