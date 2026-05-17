# HVM 資料庫結構文件

> **資料庫**：PostgreSQL  
> **更新日期**：2026-05-17  
> 標記說明：🆕 本次新增　✏️ 本次修改　✅ 原有欄位　⏳ 待建

---

## 目錄

1. [owner_groups　擁有者群組](#1-owner_groups)　🆕
2. [hvm_roles　儀表板角色](#2-hvm_roles)　🆕
3. [hosts　實體主機](#3-hosts)　✏️
4. [host_metrics　主機資源指標](#4-host_metrics)　✅
5. [vms　虛擬機器](#5-vms)　✅
6. [vm_metrics　VM 資源指標](#6-vm_metrics)　✅
7. [vm_snapshots　快照紀錄](#7-vm_snapshots)　✅
8. [vm_replication　複寫狀態](#8-vm_replication)　✅
9. [backup_jobs　備份作業](#9-backup_jobs)　✅
10. [security_events　資安事件](#10-security_events)　✅
11. [alert_rules　告警規則](#11-alert_rules)　✅
12. [app_settings　應用程式設定](#12-app_settings)　✅
13. [hvm_users VIEW　AD 使用者](#13-hvm_users-view)　⏳

---

## 1. owner_groups

擁有者群組定義表。用於區分各主機的管理歸屬單位（如 CIM、IT），
與 `hosts` 表為一對多關係。

```sql
CREATE TABLE owner_groups (
    id         SERIAL       PRIMARY KEY,
    name       VARCHAR(64)  NOT NULL UNIQUE,  -- 群組名稱，例如 'CIM'、'IT'
    created_at TIMESTAMP    NOT NULL DEFAULT NOW()  -- 建立時間
);

-- 預設資料
INSERT INTO owner_groups (name) VALUES ('CIM'), ('IT');
```

| 欄位 | 型態 | 說明 |
|---|---|---|
| `id` | SERIAL | 主鍵，自動遞增 |
| `name` | VARCHAR(64) | 群組名稱，不可重複，例如 `CIM`、`IT` |
| `created_at` | TIMESTAMP | 建立時間，預設當下時間 |

---

## 2. hvm_roles

儀表板使用者角色表。AD 認證通過後，查此表決定使用者在 HVM 的權限。
未在此表的 AD 帳號視為一般使用者（預設 `user`）。

```sql
CREATE TABLE hvm_roles (
    username   VARCHAR(64)  PRIMARY KEY,              -- AD 登入帳號（不含網域）
    role       VARCHAR(16)  NOT NULL DEFAULT 'user',  -- 角色：'admin' | 'user'
    created_at TIMESTAMP    NOT NULL DEFAULT NOW()    -- 建立時間
);
```

| 欄位 | 型態 | 說明 |
|---|---|---|
| `username` | VARCHAR(64) | AD 登入帳號，主鍵（不含網域，例如 `john.doe`） |
| `role` | VARCHAR(16) | 角色：`admin`（管理員）或 `user`（一般使用者） |
| `created_at` | TIMESTAMP | 建立時間 |

**角色權限說明**

| 角色 | 可存取頁面 |
|---|---|
| `user` | 總覽、資源監控、快照合規、備份/HA、資安監控（唯讀） |
| `admin` | 全部頁面，含告警設定、系統設定、管理帳號 |

---

## 3. hosts

實體主機清單。包含 Hyper-V 宿主機與一般 Windows Server。
由排程器自動建立（HV_HOSTS / WS_HOSTS），也可從儀表板手動新增。

```sql
CREATE TABLE hosts (
    id             SERIAL      PRIMARY KEY,
    name           VARCHAR(64) NOT NULL UNIQUE,               -- 主機識別名稱（IP 或 Hostname）
    ip             VARCHAR(64) NOT NULL,                      -- WinRM 連線 IP
    description    TEXT,                                      -- 服務說明，例如「生產環境 Hyper-V 主機 A」
    host_type      VARCHAR(16) NOT NULL DEFAULT 'hyperv',     -- 主機類型：'hyperv' | 'windows'
    owner_group_id INTEGER     REFERENCES owner_groups(id),   -- 管理歸屬單位（FK → owner_groups）
    online         BOOLEAN     NOT NULL DEFAULT TRUE,         -- 連線狀態
    collected_at   TIMESTAMP   NOT NULL DEFAULT NOW()         -- 最後採樣時間
);

CREATE INDEX ix_hosts_name ON hosts(name);
```

| 欄位 | 型態 | 說明 |
|---|---|---|
| `id` | SERIAL | 主鍵，自動遞增 |
| `name` | VARCHAR(64) | 主機識別名稱，唯一值，通常為 IP 或 Hostname |
| `ip` | VARCHAR(64) | WinRM 連線用 IP 位址 |
| `description` | TEXT | 服務說明，人工填寫，例如「廠區 A HV 主機」 |
| `host_type` | VARCHAR(16) | 主機類型：`hyperv`（Hyper-V 宿主機）或 `windows`（一般 Windows Server） |
| `owner_group_id` | INTEGER | FK → `owner_groups.id`，管理歸屬單位，可為 NULL |
| `online` | BOOLEAN | 最後採樣是否連線成功 |
| `collected_at` | TIMESTAMP | 最後一次成功採樣的時間 |

---

## 4. host_metrics

實體主機資源使用量，每 15 分鐘採樣一次寫入。

```sql
CREATE TABLE host_metrics (
    id               SERIAL    PRIMARY KEY,
    host_id          INTEGER   NOT NULL REFERENCES hosts(id),  -- 所屬主機（FK → hosts）
    cpu_pct          FLOAT     NOT NULL,                       -- CPU 使用率（%）
    ram_used_gb      FLOAT     NOT NULL,                       -- 已用記憶體（GB）
    ram_total_gb     FLOAT     NOT NULL,                       -- 總記憶體（GB）
    storage_used_tb  FLOAT     NOT NULL,                       -- C 槽已用空間（TB）
    storage_total_tb FLOAT     NOT NULL,                       -- C 槽總容量（TB）
    collected_at     TIMESTAMP NOT NULL DEFAULT NOW()          -- 採樣時間
);

CREATE INDEX ix_host_metrics_host_id      ON host_metrics(host_id);
CREATE INDEX ix_host_metrics_collected_at ON host_metrics(collected_at);
```

| 欄位 | 型態 | 說明 |
|---|---|---|
| `id` | SERIAL | 主鍵 |
| `host_id` | INTEGER | FK → `hosts.id` |
| `cpu_pct` | FLOAT | CPU 整體使用率（`\Processor(_Total)\% Processor Time`） |
| `ram_used_gb` | FLOAT | 已使用記憶體（GB） |
| `ram_total_gb` | FLOAT | 實體記憶體總量（GB） |
| `storage_used_tb` | FLOAT | C 槽已用空間（TB） |
| `storage_total_tb` | FLOAT | C 槽總容量（TB） |
| `collected_at` | TIMESTAMP | 採樣時間 |

---

## 5. vms

虛擬機器清單，由 `Get-VM` 取得並同步。名稱統一大寫儲存。

```sql
CREATE TABLE vms (
    id      SERIAL      PRIMARY KEY,
    name    VARCHAR(64) NOT NULL UNIQUE,           -- VM 名稱（大寫正規化）
    host_id INTEGER     NOT NULL REFERENCES hosts(id),  -- 所屬宿主機（FK → hosts）
    vcpu    INTEGER     NOT NULL,                  -- 配置的虛擬 CPU 數量
    ram_gb  FLOAT       NOT NULL,                  -- 配置的記憶體（GB）
    tier    VARCHAR(16) NOT NULL DEFAULT 'Tier2',  -- 服務等級：'Tier1' | 'Tier2'
    is_sql  BOOLEAN     NOT NULL DEFAULT FALSE,    -- 是否為 SQL Server VM（快照即違規）
    state   VARCHAR(32) NOT NULL DEFAULT 'Running' -- VM 狀態（Running / Off / Saved 等）
);

CREATE INDEX ix_vms_name ON vms(name);
```

| 欄位 | 型態 | 說明 |
|---|---|---|
| `id` | SERIAL | 主鍵 |
| `name` | VARCHAR(64) | VM 名稱，統一大寫，唯一值 |
| `host_id` | INTEGER | FK → `hosts.id`，所屬 Hyper-V 宿主機 |
| `vcpu` | INTEGER | 配置的 vCPU 核心數 |
| `ram_gb` | FLOAT | 配置的記憶體大小（GB） |
| `tier` | VARCHAR(16) | 服務等級：`Tier1`（關鍵）或 `Tier2`（一般） |
| `is_sql` | BOOLEAN | `TRUE` 表示 SQL Server VM，有快照即判定為嚴重違規 |
| `state` | VARCHAR(32) | VM 執行狀態（來自 Hyper-V `Get-VM`） |

---

## 6. vm_metrics

VM 資源使用量，每 15 分鐘採樣一次。

```sql
CREATE TABLE vm_metrics (
    id               SERIAL    PRIMARY KEY,
    vm_id            INTEGER   NOT NULL REFERENCES vms(id),  -- 所屬 VM（FK → vms）
    cpu_pct          FLOAT     NOT NULL,                     -- vCPU 平均使用率（%）
    ram_used_gb      FLOAT     NOT NULL,                     -- 宿主機分配給 VM 的記憶體（GB）
    ram_pressure_pct FLOAT,                                  -- RAM 壓力百分比（可為 NULL）
    net_in_kbps      FLOAT     NOT NULL DEFAULT 0,           -- 網路接收速率（KB/s）
    net_out_kbps     FLOAT     NOT NULL DEFAULT 0,           -- 網路傳送速率（KB/s）
    collected_at     TIMESTAMP NOT NULL DEFAULT NOW()        -- 採樣時間
);

CREATE INDEX ix_vm_metrics_vm_id        ON vm_metrics(vm_id);
CREATE INDEX ix_vm_metrics_collected_at ON vm_metrics(collected_at);
```

| 欄位 | 型態 | 說明 |
|---|---|---|
| `id` | SERIAL | 主鍵 |
| `vm_id` | INTEGER | FK → `vms.id` |
| `cpu_pct` | FLOAT | 所有 vCPU 的平均 Guest Run Time（%） |
| `ram_used_gb` | FLOAT | 宿主機 MemoryAssigned 值（GB） |
| `ram_pressure_pct` | FLOAT | RAM 壓力（%）；IS 正常時 = Demand/Assigned，IS 故障時由直連 Guest OS 計算，無法取得時為 NULL |
| `net_in_kbps` | FLOAT | 所有虛擬網卡接收速率加總（KB/s） |
| `net_out_kbps` | FLOAT | 所有虛擬網卡傳送速率加總（KB/s） |
| `collected_at` | TIMESTAMP | 採樣時間 |

---

## 7. vm_snapshots

VM 快照紀錄，每 15 分鐘由 `Get-VMSnapshot` 採集，去重後寫入。

```sql
CREATE TABLE vm_snapshots (
    id            SERIAL       PRIMARY KEY,
    vm_id         INTEGER      NOT NULL REFERENCES vms(id),  -- 所屬 VM（FK → vms）
    snapshot_name VARCHAR(256) NOT NULL,                     -- 快照名稱
    created_at    TIMESTAMP    NOT NULL,                     -- 快照建立時間（來自 Hyper-V）
    detected_at   TIMESTAMP    NOT NULL DEFAULT NOW()        -- 系統首次偵測到此快照的時間
);

CREATE INDEX ix_vm_snapshots_vm_id      ON vm_snapshots(vm_id);
CREATE INDEX ix_vm_snapshots_created_at ON vm_snapshots(created_at);
```

| 欄位 | 型態 | 說明 |
|---|---|---|
| `id` | SERIAL | 主鍵 |
| `vm_id` | INTEGER | FK → `vms.id` |
| `snapshot_name` | VARCHAR(256) | 快照名稱（`Get-VMSnapshot` 回傳） |
| `created_at` | TIMESTAMP | 快照實際建立時間（用於計算存在天數） |
| `detected_at` | TIMESTAMP | 系統首次偵測到此快照的時間 |

**快照合規規則**

| VM 類型 | 條件 | 判定 |
|---|---|---|
| SQL Server（`is_sql=TRUE`） | 有任何快照 | 🔴 嚴重違規 |
| 一般 VM | 快照存在 > 7 天 | 🔴 嚴重違規 |
| 一般 VM | 快照存在 3–7 天 | 🟡 警告 |
| 一般 VM | 快照存在 ≤ 3 天 | 🟢 合規 |

---

## 8. vm_replication

VM Hyper-V 複寫狀態，每 15 分鐘由 `Get-VMReplication` 採集。

```sql
CREATE TABLE vm_replication (
    id                    SERIAL      PRIMARY KEY,
    vm_id                 INTEGER     NOT NULL REFERENCES vms(id),  -- 所屬 VM（FK → vms）
    replication_state     VARCHAR(64) NOT NULL,   -- 複寫作業狀態
    replication_health    VARCHAR(64) NOT NULL,   -- 複寫健康狀態
    last_replication_time TIMESTAMP,              -- 最後一次成功複寫的時間
    rpo_minutes           INTEGER     NOT NULL DEFAULT 15,  -- RPO 目標（分鐘）
    collected_at          TIMESTAMP   NOT NULL DEFAULT NOW()  -- 採樣時間
);

CREATE INDEX ix_vm_replication_vm_id        ON vm_replication(vm_id);
CREATE INDEX ix_vm_replication_collected_at ON vm_replication(collected_at);
```

| 欄位 | 型態 | 說明 |
|---|---|---|
| `id` | SERIAL | 主鍵 |
| `vm_id` | INTEGER | FK → `vms.id` |
| `replication_state` | VARCHAR(64) | 複寫作業狀態，例如 `Normal`、`Error`、`Suspended` |
| `replication_health` | VARCHAR(64) | 複寫健康，例如 `Normal`、`Warning`、`Critical` |
| `last_replication_time` | TIMESTAMP | 最後成功複寫時間，用於計算落後時間 |
| `rpo_minutes` | INTEGER | RPO 目標值（分鐘），預設 15 分鐘 |
| `collected_at` | TIMESTAMP | 採樣時間 |

---

## 9. backup_jobs

Veeam 備份作業結果（待 Veeam 採購確認後實作採集）。

```sql
CREATE TABLE backup_jobs (
    id           SERIAL       PRIMARY KEY,
    vm_id        INTEGER      NOT NULL REFERENCES vms(id),  -- 所屬 VM（FK → vms）
    job_name     VARCHAR(128) NOT NULL,  -- Veeam 備份 Job 名稱
    result       VARCHAR(32)  NOT NULL,  -- 作業結果
    start_time   TIMESTAMP    NOT NULL,  -- 備份開始時間
    end_time     TIMESTAMP,              -- 備份結束時間（進行中時為 NULL）
    collected_at TIMESTAMP    NOT NULL DEFAULT NOW()  -- 寫入時間
);

CREATE INDEX ix_backup_jobs_vm_id        ON backup_jobs(vm_id);
CREATE INDEX ix_backup_jobs_collected_at ON backup_jobs(collected_at);
```

| 欄位 | 型態 | 說明 |
|---|---|---|
| `id` | SERIAL | 主鍵 |
| `vm_id` | INTEGER | FK → `vms.id` |
| `job_name` | VARCHAR(128) | Veeam 備份 Job 名稱 |
| `result` | VARCHAR(32) | 作業結果：`Success`、`Failed`、`Warning` |
| `start_time` | TIMESTAMP | 備份開始時間 |
| `end_time` | TIMESTAMP | 備份結束時間，進行中時為 NULL |
| `collected_at` | TIMESTAMP | 資料寫入時間 |

---

## 10. security_events

Windows 安全事件紀錄，每 5 分鐘採集一次，去重後寫入。

```sql
CREATE TABLE security_events (
    id           SERIAL       PRIMARY KEY,
    source_host  VARCHAR(64)  NOT NULL,           -- 事件來源主機（IP 或 Hostname）
    event_id     INTEGER      NOT NULL,            -- Windows Event ID
    event_type   VARCHAR(64)  NOT NULL,            -- 事件分類
    account      VARCHAR(128) NOT NULL,            -- 相關帳號
    description  TEXT         NOT NULL DEFAULT '', -- 事件說明
    severity     VARCHAR(16)  NOT NULL DEFAULT 'warn',  -- 嚴重度
    occurred_at  TIMESTAMP    NOT NULL,            -- 事件發生時間
    collected_at TIMESTAMP    NOT NULL DEFAULT NOW()    -- 採集時間
);

CREATE INDEX ix_security_events_source_host ON security_events(source_host);
CREATE INDEX ix_security_events_event_id    ON security_events(event_id);
CREATE INDEX ix_security_events_occurred_at ON security_events(occurred_at);
```

| 欄位 | 型態 | 說明 |
|---|---|---|
| `id` | SERIAL | 主鍵 |
| `source_host` | VARCHAR(64) | 事件來源主機 IP 或名稱 |
| `event_id` | INTEGER | Windows Event ID（4624 / 4625 / 4728 / 4732 / 4740） |
| `event_type` | VARCHAR(64) | 分類：`login_success`、`login_fail`、`lockout`、`group_change` |
| `account` | VARCHAR(128) | 事件相關帳號 |
| `description` | TEXT | 事件說明文字 |
| `severity` | VARCHAR(16) | 嚴重度：`err`、`warn`、`info` |
| `occurred_at` | TIMESTAMP | 事件實際發生時間（來自 Windows Event Log） |
| `collected_at` | TIMESTAMP | 系統採集並寫入的時間 |

**Event ID 對應**

| Event ID | 分類 | 嚴重度 |
|---|---|---|
| 4624 | `login_success` | `info` |
| 4625 | `login_fail` | `warn` / `err` |
| 4728 | `group_change` | `err` |
| 4732 | `group_change` | `err` |
| 4740 | `lockout` | `err` |

---

## 11. alert_rules

告警規則設定，由前端儀表板管理。首次啟動時自動寫入預設規則。

```sql
CREATE TABLE alert_rules (
    id               SERIAL       PRIMARY KEY,
    rule_name        VARCHAR(128) NOT NULL UNIQUE,  -- 規則名稱
    category         VARCHAR(64)  NOT NULL,          -- 規則分類
    enabled          BOOLEAN      NOT NULL DEFAULT TRUE,  -- 是否啟用
    severity         VARCHAR(16)  NOT NULL,          -- 嚴重度
    threshold_value  FLOAT,                          -- 門檻數值（NULL 表示觸發即告警）
    threshold_unit   VARCHAR(32),                    -- 門檻單位說明
    notify_immediate BOOLEAN      NOT NULL DEFAULT TRUE,  -- 是否即時通知
    description      TEXT         NOT NULL DEFAULT '',    -- 規則說明
    updated_at       TIMESTAMP    NOT NULL DEFAULT NOW()  -- 最後修改時間
);
```

| 欄位 | 型態 | 說明 |
|---|---|---|
| `id` | SERIAL | 主鍵 |
| `rule_name` | VARCHAR(128) | 規則名稱，唯一值 |
| `category` | VARCHAR(64) | 分類：`resource`、`snapshot`、`backup`、`security` |
| `enabled` | BOOLEAN | 是否啟用此規則 |
| `severity` | VARCHAR(16) | 嚴重度：`err`（嚴重）或 `warn`（警告） |
| `threshold_value` | FLOAT | 門檻數值；`NULL` 表示事件發生即觸發 |
| `threshold_unit` | VARCHAR(32) | 門檻單位說明，例如 `%`、`天`、`次/10min` |
| `notify_immediate` | BOOLEAN | `TRUE` = 即時通知；`FALSE` = 彙整後通知 |
| `description` | TEXT | 規則說明文字 |
| `updated_at` | TIMESTAMP | 最後修改時間 |

---

## 12. app_settings

應用程式 Key-Value 設定儲存。UI 儲存的通知設定（SMTP / Webhook）存於此表，
優先權高於 `.env` 檔案。

```sql
CREATE TABLE app_settings (
    id         SERIAL       PRIMARY KEY,
    key        VARCHAR(128) NOT NULL UNIQUE,  -- 設定鍵名
    value      TEXT         NOT NULL DEFAULT '',  -- 設定值（字串，布林值存 'true'/'false'）
    updated_at TIMESTAMP    NOT NULL DEFAULT NOW()  -- 最後更新時間
);

CREATE INDEX ix_app_settings_key ON app_settings(key);
```

| 欄位 | 型態 | 說明 |
|---|---|---|
| `id` | SERIAL | 主鍵 |
| `key` | VARCHAR(128) | 設定鍵名，唯一值（例如 `smtp_host`、`alert_email_it`） |
| `value` | TEXT | 設定值，統一以字串儲存（布林值存 `true`/`false`） |
| `updated_at` | TIMESTAMP | 最後更新時間 |

**常用 Key 清單**

| Key | 說明 |
|---|---|
| `smtp_host` | SMTP 主機位址 |
| `smtp_port` | SMTP 連接埠 |
| `smtp_sender_email` | 寄件人信箱 |
| `smtp_sender_name` | 寄件人顯示名稱 |
| `alert_email_it` | IT 工程師收件信箱（逗號分隔多位） |
| `alert_email_manager` | 主管收件信箱（逗號分隔多位） |
| `daily_report_time` | 每日報告發送時間（HH:MM） |
| `webhook_enable` | Webhook 推播開關（`true`/`false`） |
| `webhook_url` | Webhook 推播 URL |
| `webhook_token` | Webhook 驗證 Token |

---

## 13. hvm_users VIEW

AD 使用者視圖，由現有 AD 資料庫的 TABLE 映射而來。
**待確認 AD TABLE 欄位後建立。**

```sql
-- 範本，欄位名稱待確認後替換
CREATE VIEW hvm_users AS
SELECT
    <ad_account_column>    AS username,      -- AD 登入帳號
    <ad_dept_column>       AS department,    -- 所屬部門
    <ad_name_column>       AS display_name,  -- 顯示名稱
    <ad_email_column>      AS email          -- 電子郵件
FROM <your_ad_table>
WHERE <dept_filter_condition>;               -- 限定有存取權的部門
```

**認證流程說明**

```
使用者輸入帳密
    │
    ├─ LDAP Bind 驗證密碼（不存密碼在 DB）
    │
    ├─ 查 hvm_users VIEW → 確認帳號存在 + 讀取部門
    │
    └─ 查 hvm_roles TABLE → 取得 HVM 角色（無記錄預設 'user'）
```

---

## 建表執行順序

由於存在 FK 關聯，請依以下順序執行：

```
1. owner_groups
2. hvm_roles
3. hosts          （依賴 owner_groups）
4. host_metrics   （依賴 hosts）
5. vms            （依賴 hosts）
6. vm_metrics     （依賴 vms）
7. vm_snapshots   （依賴 vms）
8. vm_replication （依賴 vms）
9. backup_jobs    （依賴 vms）
10. security_events
11. alert_rules
12. app_settings
13. hvm_users VIEW （待 AD 欄位確認後建立）
```
