# WinRM 連線測試指南

**用途**：驗證管理端可透過 WinRM 遠端查詢 Hyper-V 宿主機，為 Collector 上線做準備
**執行時機**：部署 AP Server 前的環境確認

---

## 環境說明

```
[你的測試機 / 未來管理 VM]
        │
        │ WinRM（TCP 5985）
        ▼
[Hyper-V 宿主機 KHFACVS01]
[Hyper-V 宿主機 KHFACVS02]
```

> **Note**：AP Server（管理 VM）最終規格為 2 vCPU / 4 GB RAM，部署 FastAPI + Collector，不要裝在 Hyper-V 宿主機上。

---

## Step 1：宿主機端確認 WinRM（在 Hyper-V 宿主機上執行）

以系統管理員身分開啟 PowerShell，依序執行：

```powershell
# 1-1 確認 WinRM 服務狀態（應為 Running）
Get-Service WinRM
```

```powershell
# 1-2 若服務未啟動，執行快速設定（會自動啟用並設定防火牆）
winrm quickconfig
# 出現提示時輸入 Y 確認
```

```powershell
# 1-3 確認監聽器已建立（應看到 Transport = HTTP，Port = 5985）
winrm enumerate winrm/config/Listener
```

```powershell
# 1-4 確認防火牆規則已啟用
Get-NetFirewallRule -DisplayName "*Windows Remote Management*" |
    Select-Object DisplayName, Enabled, Direction
```

```powershell
# 1-5 確認宿主機已安裝 Hyper-V PowerShell 模組
Get-Module -ListAvailable -Name Hyper-V | Select-Object Name, Version
```

**預期結果：**
- WinRM 服務 Status = `Running`
- 監聽器 Port = `5985`，Transport = `HTTP`
- Hyper-V 模組版本應對應 Windows Server 版本

---

## Step 2：從管理端測試網路連通（在測試機 / 管理 VM 上執行）

```powershell
# 2-1 Ping 測試（確認網路可達）
ping 192.168.1.101   # 換成實際 IP
ping 192.168.1.102
```

```powershell
# 2-2 確認 WinRM 連接埠可達（應顯示 TcpTestSucceeded : True）
Test-NetConnection -ComputerName 192.168.1.101 -Port 5985
```

```powershell
# 2-3 WinRM 協議測試（應回傳宿主機的 WinRM 資訊）
Test-WSMan -ComputerName 192.168.1.101 -Authentication Negotiate
```

**若 Test-WSMan 失敗，在管理端執行：**

```powershell
# 將宿主機加入本機 TrustedHosts（非 Domain 環境需要此步驟）
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "192.168.1.101,192.168.1.102" -Force

# 確認設定
Get-Item WSMan:\localhost\Client\TrustedHosts
```

---

## Step 3：PowerShell 遠端互動測試

```powershell
# 3-1 建立互動式遠端 Session（輸入帳號密碼後進入遠端 PS 提示字元）
Enter-PSSession -ComputerName 192.168.1.101 -Credential (Get-Credential)
```

進入遠端 Session 後，確認以下指令可正常執行：

```powershell
# 確認是在宿主機上
hostname

# 取得所有 VM
Get-VM | Select-Object Name, State, ProcessorCount,
    @{N='MemoryGB';E={[math]::Round($_.MemoryAssigned/1GB,1)}}

# 取得所有快照
Get-VMSnapshot -VMName * | Select-Object VMName, Name, CreationTime

# 取得複寫狀態（若有設定）
Get-VMReplication | Select-Object VMName, State, Health, LastReplicationTime

# 離開遠端 Session
exit
```

---

## Step 4：Python 連線測試

確認 Python 3.10+ 已安裝，執行以下步驟：

```bash
# 4-1 安裝套件（在 backend/ 目錄下）
cd /path/to/hyperVmonitor/backend
pip install -r requirements.txt
```

```bash
# 4-2 設定環境變數（或在 .env 填入後直接執行）
export WINRM_USER=administrator
export WINRM_PASSWORD=your_password_here
export HV_HOSTS=10.10.22.187        # 換成實際 IP，逗號分隔可測多台
```

```bash
# 4-3 執行測試（腳本已內建於 backend/test_winrm.py）
python test_winrm.py
```

測試腳本會依序驗證：`whoami`、`Get-VM`、`Get-VMSnapshot`、`Get-VMReplication`、
Hyper-V 計數器、宿主機 CPU 計數器、安全性事件記錄、`Get-VMNetworkAdapter`。
全部通過後輸出彙整結果表格。

> **Note**：`Get-VMReplication` 若無回傳為正常（尚未設定複寫時）。
> 安全性事件記錄若 30 分鐘內無登入活動也可能回傳空值，均視為通過。

---

## 測試結果記錄

| 測試項目 | 結果 | 備註 |
|---|---|---|
| WinRM 服務狀態（宿主機） | ✅ 通過 | |
| TCP 5985 連通性 | ✅ 通過 | |
| Test-WSMan | ⚠️ Code=5 | UAC token 過濾，不影響實際連線 |
| Enter-PSSession | ✅ 通過 | |
| Get-VM（Python） | ⬜ 通過 / ⬜ 失敗 | |
| Get-VMSnapshot（Python） | ⬜ 通過 / ⬜ 失敗 | |
| Hyper-V 計數器（Python） | ⬜ 通過 / ⬜ 失敗 | |
| Get-VMReplication（Python） | ⬜ 通過 / ⬜ 失敗 | 未設複寫時空回傳為正常 |
| 安全性事件記錄（Python） | ⬜ 通過 / ⬜ 失敗 | |
| Get-VMNetworkAdapter（Python） | ⬜ 通過 / ⬜ 失敗 | |

---

## 常見錯誤排查

| 錯誤訊息 | 原因 | 解法 |
|---|---|---|
| `Connection refused` | WinRM 未啟動或防火牆擋 | 宿主機執行 `winrm quickconfig` |
| `401 Unauthorized` | 帳號或密碼錯誤 | 確認 administrator 帳號密碼 |
| `500 Internal Server Error` | TrustedHosts 未設定 | Step 2 補充步驟 |
| `WinRMTransportError` | NTLM 驗證問題 | 確認帳號格式（`domain\user` 或 `.\administrator`） |
| 中文 / 特殊字元亂碼 | 編碼問題 | `WinRMClient` 已處理 cp950，回報錯誤內容 |
| `Cannot find module 'Hyper-V'` | 宿主機缺少模組 | `Install-WindowsFeature Hyper-V-PowerShell` |
| `Get-VMReplication` 無回傳 | 未設定複寫 | 正常，不影響其他功能 |

---

## 測試完成後的下一步

全部測試通過後，回報測試結果，接著進行：

1. 把 `backend/routers/` 的 mock data 改為真正查詢 SQLite
2. 啟動 Collector，對舊主機進行第一次真實採樣
3. 確認資料寫入 DB 後，Dashboard 顯示真實數值
