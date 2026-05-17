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

## 建表執行順序

由於存在 FK 關聯，請依以下順序執行：

```
1.  owner_groups
2.  hvm_roles
3.  hosts          （依賴 owner_groups）
4.  host_metrics   （依賴 hosts）
5.  vms            （依賴 hosts）
6.  vm_metrics     （依賴 vms）
7.  vm_snapshots   （依賴 vms）
8.  vm_replication （依賴 vms）
9.  backup_jobs    （依賴 vms）
10. security_events
11. alert_rules
12. app_settings
13. hvm_users VIEW （待 AD 欄位確認後建立）
```

---

## 1. owner_groups

🆕 擁有者群組定義表。用於區分各主機的管理歸屬單位，與 `hosts` 表為一對多關係。

```sql
CREATE TABLE owner_groups (
    id         SERIAL      PRIMARY KEY,
    name       VARCHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMP   NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  owner_groups            IS '主機擁有者群組定義（如 CIM、IT）';
COMMENT ON COLUMN owner_groups.id         IS '主鍵，自動遞增';
COMMENT ON COLUMN owner_groups.name       IS '群組名稱，不可重複，例如 CIM、IT';
COMMENT ON COLUMN owner_groups.created_at IS '建立時間';

-- 預設資料
INSERT INTO owner_groups (name) VALUES ('CIM'), ('IT');
```

---

## 2. hvm_roles

🆕 儀表板使用者角色表。AD 認證通過後查此表決定 HVM 權限。
未在此表的 AD 帳號以 `is_local_admin` 欄位判斷，兩者皆無則預設 `user`。

```sql
CREATE TABLE hvm_roles (
    username   VARCHAR(64) PRIMARY KEY,
    role       VARCHAR(16) NOT NULL DEFAULT 'user',
    created_at TIMESTAMP   NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  hvm_roles            IS 'HVM 儀表板使用者角色設定；優先於 AD is_local_admin 欄位';
COMMENT ON COLUMN hvm_roles.username   IS 'AD 登入帳號（sAMAccountName，不含網域），對應 hvm_users.username';
COMMENT ON COLUMN hvm_roles.role       IS '角色：admin（管理員）或 user（一般使用者）';
COMMENT ON COLUMN hvm_roles.created_at IS '建立時間';
```

**角色權限說明**

| 角色 | 可存取頁面 |
|---|---|
| `user` | 總覽、資源監控、快照合規、備份/HA、資安監控（唯讀） |
| `admin` | 全部頁面，含告警設定、系統設定、管理帳號 |

**角色判斷邏輯（方案 C）**

```
hvm_roles 有記錄  →  使用 hvm_roles.role
hvm_roles 無記錄  →  is_local_admin = TRUE  →  'admin'
                  →  is_local_admin = FALSE →  'user'
```

---

## 3. hosts

✏️ 實體主機清單。包含 Hyper-V 宿主機與一般 Windows Server。
由排程器依 `.env` 設定自動建立，也可從儀表板手動新增（非 HV 主機）。

```sql
CREATE TABLE hosts (
    id             SERIAL      PRIMARY KEY,
    name           VARCHAR(64) NOT NULL UNIQUE,
    ip             VARCHAR(64) NOT NULL,
    description    TEXT,
    host_type      VARCHAR(16) NOT NULL DEFAULT 'hyperv',
    owner_group_id INTEGER     REFERENCES owner_groups(id),
    online         BOOLEAN     NOT NULL DEFAULT TRUE,
    collected_at   TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_hosts_name ON hosts(name);

COMMENT ON TABLE  hosts                IS '受監控的實體主機清單（Hyper-V 宿主機或一般 Windows Server）';
COMMENT ON COLUMN hosts.id             IS '主鍵，自動遞增';
COMMENT ON COLUMN hosts.name          IS '主機識別名稱，唯一值；自動建立時填入 IP，可改為 Hostname';
COMMENT ON COLUMN hosts.ip            IS 'WinRM 連線用 IP 位址';
COMMENT ON COLUMN hosts.description   IS '服務說明，人工填寫，例如：廠區 A 生產環境 Hyper-V 主機';
COMMENT ON COLUMN hosts.host_type     IS '主機類型：hyperv（Hyper-V 宿主機）或 windows（一般 Windows Server）';
COMMENT ON COLUMN hosts.owner_group_id IS '管理歸屬單位，FK → owner_groups.id；NULL 表示未指定';
COMMENT ON COLUMN hosts.online        IS '最後採樣是否連線成功';
COMMENT ON COLUMN hosts.collected_at  IS '最後一次成功採樣的時間';
```

---

## 4. host_metrics

✅ 實體主機資源使用量，每 15 分鐘採樣一次寫入。

```sql
CREATE TABLE host_metrics (
    id               SERIAL    PRIMARY KEY,
    host_id          INTEGER   NOT NULL REFERENCES hosts(id),
    cpu_pct          FLOAT     NOT NULL,
    ram_used_gb      FLOAT     NOT NULL,
    ram_total_gb     FLOAT     NOT NULL,
    storage_used_tb  FLOAT     NOT NULL,
    storage_total_tb FLOAT     NOT NULL,
    collected_at     TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_host_metrics_host_id      ON host_metrics(host_id);
CREATE INDEX ix_host_metrics_collected_at ON host_metrics(collected_at);

COMMENT ON TABLE  host_metrics                  IS '實體主機資源使用量，每 15 分鐘採樣';
COMMENT ON COLUMN host_metrics.id               IS '主鍵，自動遞增';
COMMENT ON COLUMN host_metrics.host_id          IS 'FK → hosts.id';
COMMENT ON COLUMN host_metrics.cpu_pct          IS 'CPU 整體使用率（%）；來源：\Processor(_Total)\% Processor Time';
COMMENT ON COLUMN host_metrics.ram_used_gb      IS '已使用記憶體（GB）；來源：Win32_OperatingSystem';
COMMENT ON COLUMN host_metrics.ram_total_gb     IS '實體記憶體總量（GB）';
COMMENT ON COLUMN host_metrics.storage_used_tb  IS 'C 槽已用空間（TB）；來源：Get-PSDrive C';
COMMENT ON COLUMN host_metrics.storage_total_tb IS 'C 槽總容量（TB）';
COMMENT ON COLUMN host_metrics.collected_at     IS '採樣時間（UTC）';
```

---

## 5. vms

✅ 虛擬機器清單，由 `Get-VM` 取得並每 15 分鐘同步。名稱統一大寫儲存。

```sql
CREATE TABLE vms (
    id      SERIAL      PRIMARY KEY,
    name    VARCHAR(64) NOT NULL UNIQUE,
    host_id INTEGER     NOT NULL REFERENCES hosts(id),
    vcpu    INTEGER     NOT NULL,
    ram_gb  FLOAT       NOT NULL,
    tier    VARCHAR(16) NOT NULL DEFAULT 'Tier2',
    is_sql  BOOLEAN     NOT NULL DEFAULT FALSE,
    state   VARCHAR(32) NOT NULL DEFAULT 'Running'
);

CREATE INDEX ix_vms_name ON vms(name);

COMMENT ON TABLE  vms         IS '虛擬機器清單；名稱統一大寫正規化，每 15 分鐘由 Get-VM 同步';
COMMENT ON COLUMN vms.id      IS '主鍵，自動遞增';
COMMENT ON COLUMN vms.name    IS 'VM 名稱，統一大寫，唯一值';
COMMENT ON COLUMN vms.host_id IS 'FK → hosts.id，所屬 Hyper-V 宿主機';
COMMENT ON COLUMN vms.vcpu    IS '配置的 vCPU 核心數';
COMMENT ON COLUMN vms.ram_gb  IS '配置的記憶體大小（GB）；動態記憶體取 MemoryAssigned';
COMMENT ON COLUMN vms.tier    IS '服務等級：Tier1（關鍵業務）或 Tier2（一般）';
COMMENT ON COLUMN vms.is_sql  IS 'TRUE 表示 SQL Server VM；有任何快照即判定為嚴重違規';
COMMENT ON COLUMN vms.state   IS 'VM 執行狀態；來源：Get-VM（Running / Off / Saved / Paused）';
```

---

## 6. vm_metrics

✅ VM 資源使用量，每 15 分鐘採樣一次。

```sql
CREATE TABLE vm_metrics (
    id               SERIAL    PRIMARY KEY,
    vm_id            INTEGER   NOT NULL REFERENCES vms(id),
    cpu_pct          FLOAT     NOT NULL,
    ram_used_gb      FLOAT     NOT NULL,
    ram_pressure_pct FLOAT,
    net_in_kbps      FLOAT     NOT NULL DEFAULT 0,
    net_out_kbps     FLOAT     NOT NULL DEFAULT 0,
    collected_at     TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_vm_metrics_vm_id        ON vm_metrics(vm_id);
CREATE INDEX ix_vm_metrics_collected_at ON vm_metrics(collected_at);

COMMENT ON TABLE  vm_metrics                  IS 'VM 資源使用量，每 15 分鐘採樣';
COMMENT ON COLUMN vm_metrics.id               IS '主鍵，自動遞增';
COMMENT ON COLUMN vm_metrics.vm_id            IS 'FK → vms.id';
COMMENT ON COLUMN vm_metrics.cpu_pct          IS '所有 vCPU 的平均 Guest Run Time（%）；來源：Hyper-V Hypervisor Virtual Processor(*)\% Guest Run Time';
COMMENT ON COLUMN vm_metrics.ram_used_gb      IS '宿主機分配給 VM 的記憶體（GB）；來源：MemoryAssigned';
COMMENT ON COLUMN vm_metrics.ram_pressure_pct IS 'RAM 壓力（%）；IS 正常：Demand/Assigned；IS 故障：直連 Guest OS 計算；無法取得時為 NULL';
COMMENT ON COLUMN vm_metrics.net_in_kbps      IS '所有虛擬網卡接收速率加總（KB/s）；來源：Hyper-V Virtual Network Adapter(*)\Bytes Received/sec';
COMMENT ON COLUMN vm_metrics.net_out_kbps     IS '所有虛擬網卡傳送速率加總（KB/s）；來源：Hyper-V Virtual Network Adapter(*)\Bytes Sent/sec';
COMMENT ON COLUMN vm_metrics.collected_at     IS '採樣時間（UTC）';
```

---

## 7. vm_snapshots

✅ VM 快照紀錄，每 15 分鐘由 `Get-VMSnapshot` 採集，去重後寫入。

```sql
CREATE TABLE vm_snapshots (
    id            SERIAL       PRIMARY KEY,
    vm_id         INTEGER      NOT NULL REFERENCES vms(id),
    snapshot_name VARCHAR(256) NOT NULL,
    created_at    TIMESTAMP    NOT NULL,
    detected_at   TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_vm_snapshots_vm_id      ON vm_snapshots(vm_id);
CREATE INDEX ix_vm_snapshots_created_at ON vm_snapshots(created_at);

COMMENT ON TABLE  vm_snapshots               IS 'VM 快照紀錄；每 15 分鐘採集，依 vm_id + snapshot_name 去重';
COMMENT ON COLUMN vm_snapshots.id            IS '主鍵，自動遞增';
COMMENT ON COLUMN vm_snapshots.vm_id         IS 'FK → vms.id';
COMMENT ON COLUMN vm_snapshots.snapshot_name IS '快照名稱；來源：Get-VMSnapshot';
COMMENT ON COLUMN vm_snapshots.created_at    IS '快照實際建立時間；用於計算存在天數，判斷合規狀態';
COMMENT ON COLUMN vm_snapshots.detected_at   IS '系統首次偵測到此快照的時間';
```

**快照合規規則**

| VM 類型 | 條件 | 判定 |
|---|---|---|
| SQL Server（`is_sql = TRUE`） | 有任何快照 | 🔴 嚴重違規 |
| 一般 VM | 快照存在 > 7 天 | 🔴 嚴重違規 |
| 一般 VM | 快照存在 3–7 天 | 🟡 警告 |
| 一般 VM | 快照存在 ≤ 3 天 | 🟢 合規 |

---

## 8. vm_replication

✅ VM Hyper-V 複寫狀態，每 15 分鐘由 `Get-VMReplication` 採集。

```sql
CREATE TABLE vm_replication (
    id                    SERIAL      PRIMARY KEY,
    vm_id                 INTEGER     NOT NULL REFERENCES vms(id),
    replication_state     VARCHAR(64) NOT NULL,
    replication_health    VARCHAR(64) NOT NULL,
    last_replication_time TIMESTAMP,
    rpo_minutes           INTEGER     NOT NULL DEFAULT 15,
    collected_at          TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_vm_replication_vm_id        ON vm_replication(vm_id);
CREATE INDEX ix_vm_replication_collected_at ON vm_replication(collected_at);

COMMENT ON TABLE  vm_replication                       IS 'VM 複寫狀態；每 15 分鐘由 Get-VMReplication 採集';
COMMENT ON COLUMN vm_replication.id                    IS '主鍵，自動遞增';
COMMENT ON COLUMN vm_replication.vm_id                 IS 'FK → vms.id';
COMMENT ON COLUMN vm_replication.replication_state     IS '複寫作業狀態；來源：Get-VMReplication（Normal / Error / Suspended）';
COMMENT ON COLUMN vm_replication.replication_health    IS '複寫健康狀態；來源：Get-VMReplication（Normal / Warning / Critical）';
COMMENT ON COLUMN vm_replication.last_replication_time IS '最後成功複寫時間；用於計算落後分鐘數';
COMMENT ON COLUMN vm_replication.rpo_minutes           IS 'RPO 目標值（分鐘）；預設 15 分鐘';
COMMENT ON COLUMN vm_replication.collected_at          IS '採樣時間（UTC）';
```

---

## 9. backup_jobs

✅ Veeam 備份作業結果。（採集器待 Veeam 採購確認後實作）

```sql
CREATE TABLE backup_jobs (
    id           SERIAL       PRIMARY KEY,
    vm_id        INTEGER      NOT NULL REFERENCES vms(id),
    job_name     VARCHAR(128) NOT NULL,
    result       VARCHAR(32)  NOT NULL,
    start_time   TIMESTAMP    NOT NULL,
    end_time     TIMESTAMP,
    collected_at TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_backup_jobs_vm_id        ON backup_jobs(vm_id);
CREATE INDEX ix_backup_jobs_collected_at ON backup_jobs(collected_at);

COMMENT ON TABLE  backup_jobs             IS 'Veeam 備份作業結果；採集器待 Veeam 採購確認後實作';
COMMENT ON COLUMN backup_jobs.id          IS '主鍵，自動遞增';
COMMENT ON COLUMN backup_jobs.vm_id       IS 'FK → vms.id';
COMMENT ON COLUMN backup_jobs.job_name    IS 'Veeam 備份 Job 名稱';
COMMENT ON COLUMN backup_jobs.result      IS '作業結果：Success / Failed / Warning';
COMMENT ON COLUMN backup_jobs.start_time  IS '備份開始時間';
COMMENT ON COLUMN backup_jobs.end_time    IS '備份結束時間；進行中時為 NULL';
COMMENT ON COLUMN backup_jobs.collected_at IS '資料寫入時間（UTC）';
```

---

## 10. security_events

✅ Windows 安全事件紀錄，每 5 分鐘採集，依來源主機 + Event ID + 發生時間去重。

```sql
CREATE TABLE security_events (
    id           SERIAL       PRIMARY KEY,
    source_host  VARCHAR(64)  NOT NULL,
    event_id     INTEGER      NOT NULL,
    event_type   VARCHAR(64)  NOT NULL,
    account      VARCHAR(128) NOT NULL,
    description  TEXT         NOT NULL DEFAULT '',
    severity     VARCHAR(16)  NOT NULL DEFAULT 'warn',
    occurred_at  TIMESTAMP    NOT NULL,
    collected_at TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_security_events_source_host ON security_events(source_host);
CREATE INDEX ix_security_events_event_id    ON security_events(event_id);
CREATE INDEX ix_security_events_occurred_at ON security_events(occurred_at);

COMMENT ON TABLE  security_events             IS 'Windows 安全事件紀錄；每 5 分鐘採集，依來源主機 + Event ID + 發生時間去重';
COMMENT ON COLUMN security_events.id          IS '主鍵，自動遞增';
COMMENT ON COLUMN security_events.source_host IS '事件來源主機 IP 或名稱';
COMMENT ON COLUMN security_events.event_id    IS 'Windows Event ID（4624 / 4625 / 4728 / 4732 / 4740）';
COMMENT ON COLUMN security_events.event_type  IS '事件分類：login_success / login_fail / lockout / group_change';
COMMENT ON COLUMN security_events.account     IS '事件相關帳號（Windows Security Log 中的 SubjectUserName）';
COMMENT ON COLUMN security_events.description IS '事件說明文字';
COMMENT ON COLUMN security_events.severity    IS '嚴重度：err（嚴重）/ warn（警告）/ info（資訊）';
COMMENT ON COLUMN security_events.occurred_at IS '事件實際發生時間（來自 Windows Event Log TimeCreated）';
COMMENT ON COLUMN security_events.collected_at IS '系統採集並寫入的時間（UTC）';
```

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

✅ 告警規則設定，由前端儀表板管理。首次啟動時自動寫入預設規則。

```sql
CREATE TABLE alert_rules (
    id               SERIAL       PRIMARY KEY,
    rule_name        VARCHAR(128) NOT NULL UNIQUE,
    category         VARCHAR(64)  NOT NULL,
    enabled          BOOLEAN      NOT NULL DEFAULT TRUE,
    severity         VARCHAR(16)  NOT NULL,
    threshold_value  FLOAT,
    threshold_unit   VARCHAR(32),
    notify_immediate BOOLEAN      NOT NULL DEFAULT TRUE,
    description      TEXT         NOT NULL DEFAULT '',
    updated_at       TIMESTAMP    NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  alert_rules                  IS '告警規則設定；首次啟動自動寫入預設規則，可從儀表板調整';
COMMENT ON COLUMN alert_rules.id               IS '主鍵，自動遞增';
COMMENT ON COLUMN alert_rules.rule_name        IS '規則名稱，唯一值，顯示於儀表板';
COMMENT ON COLUMN alert_rules.category         IS '規則分類：resource / snapshot / backup / security';
COMMENT ON COLUMN alert_rules.enabled          IS '是否啟用此規則';
COMMENT ON COLUMN alert_rules.severity         IS '嚴重度：err（嚴重）或 warn（警告）';
COMMENT ON COLUMN alert_rules.threshold_value  IS '門檻數值；NULL 表示事件發生即觸發，不需比較數值';
COMMENT ON COLUMN alert_rules.threshold_unit   IS '門檻單位說明，例如 %、天、次/10min；NULL 表示無門檻';
COMMENT ON COLUMN alert_rules.notify_immediate IS 'TRUE = 觸發即時通知；FALSE = 彙整後於排程時間發送';
COMMENT ON COLUMN alert_rules.description      IS '規則說明文字，顯示於儀表板告警設定頁';
COMMENT ON COLUMN alert_rules.updated_at       IS '最後修改時間（UTC）';
```

---

## 12. app_settings

✅ 應用程式 Key-Value 設定儲存。UI 儲存的通知設定（SMTP / Webhook）存於此表，優先權高於 `.env`。

```sql
CREATE TABLE app_settings (
    id         SERIAL       PRIMARY KEY,
    key        VARCHAR(128) NOT NULL UNIQUE,
    value      TEXT         NOT NULL DEFAULT '',
    updated_at TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_app_settings_key ON app_settings(key);

COMMENT ON TABLE  app_settings            IS '應用程式 Key-Value 設定；由儀表板 UI 寫入，優先於 .env 環境變數';
COMMENT ON COLUMN app_settings.id         IS '主鍵，自動遞增';
COMMENT ON COLUMN app_settings.key        IS '設定鍵名，唯一值（例如 smtp_host、alert_email_it）';
COMMENT ON COLUMN app_settings.value      IS '設定值，統一以字串儲存；布林值存 true/false，數字存數字字串';
COMMENT ON COLUMN app_settings.updated_at IS '最後更新時間（UTC）';
```

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
| `webhook_enable` | Webhook 推播開關（`true` / `false`） |
| `webhook_url` | Webhook 推播 URL |
| `webhook_token` | Webhook 驗證 Token |
| `webhook_body_template` | Webhook Body 模板（含 `{{$variable}}` 佔位符） |

---

## 13. hvm_users VIEW

⏳ AD 使用者視圖，從現有 AD 資料庫的 `public.users` 映射而來。
密碼驗證透過 LDAP NTLM Bind，VIEW 僅提供使用者資訊與角色判斷所需欄位。

```sql
CREATE OR REPLACE VIEW hvm_users AS
SELECT
    username,        -- AD 登入帳號（sAMAccountName）
    display_name,    -- 顯示名稱
    email,           -- 電子郵件
    department,      -- 所屬部門
    title,           -- 職稱（顯示用）
    is_local_admin   -- 本機管理員旗標（角色判斷 fallback 用）
FROM public.users
WHERE <你的部門過濾條件>;

COMMENT ON VIEW hvm_users IS 'AD 使用者視圖；LDAP NTLM 驗證通過後查此 VIEW 確認存取權與角色';
```

**AD 認證流程**

```
使用者輸入 username + password
    │
    ├─ LDAP NTLM Bind（ldap3）→ 驗證密碼
    │   └─ 失敗 → 嘗試本機管理員（SHA-256，存於 .env）
    │
    ├─ 查 hvm_users VIEW → 確認帳號在允許部門內
    │
    └─ 決定 HVM 角色
        ├─ hvm_roles 有記錄  → 使用 hvm_roles.role
        └─ hvm_roles 無記錄  → is_local_admin = TRUE  → 'admin'
                             → is_local_admin = FALSE → 'user'

    → 簽發 JWT（httpOnly Cookie）
    → payload：{ username, role, display_name }
```

**JWT 相關 .env 設定**

```env
# AD / LDAP
LDAP_SERVER=ldap://your-ad-server
LDAP_DOMAIN=COMPANY
LDAP_BASE_DN=DC=company,DC=local

# JWT
SECRET_KEY=請換成隨機長字串
ACCESS_TOKEN_EXPIRE_MINUTES=480

# 本機管理員（LDAP 故障時 fallback）
LOCAL_ADMIN_USERNAME=hvm_admin
LOCAL_ADMIN_PASSWORD_HASH=   # hashlib.sha256("密碼".encode()).hexdigest()
```
