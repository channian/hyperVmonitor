# VM 計數器診斷指南

**用途**：確認 Hyper-V 效能計數器的 instance 名稱格式，供修正 CPU / 網路採集邏輯使用。

---

## 執行環境

在 **Hyper-V 宿主機**上，以系統管理員身分開啟 PowerShell。

---

## Step 1：VM CPU 計數器

```powershell
(Get-Counter '\Hyper-V Hypervisor Virtual Processor(*)\% Guest Run Time' `
    -ErrorAction SilentlyContinue).CounterSamples |
    Select-Object InstanceName, CookedValue |
    Format-Table -AutoSize
```

**預期輸出範例：**

```
InstanceName          CookedValue
------------          -----------
vmname:hv vp 0        12.34
vmname:hv vp 1         8.21
vmname2:hv vp 0        45.6
_total                  ...
```

**記錄重點：**
- `InstanceName` 的格式（VM 名稱與 VP 編號之間的分隔符）
- VM 名稱是大寫還是小寫
- 是否有 `_total` 或其他非 VM 的項目

---

## Step 2：網路計數器

```powershell
(Get-Counter '\Hyper-V Virtual Network Adapter(*)\Bytes Received/sec' `
    -ErrorAction SilentlyContinue).CounterSamples |
    Select-Object InstanceName, CookedValue |
    Format-Table -AutoSize
```

**預期輸出範例：**

```
InstanceName                        CookedValue
------------                        -----------
vmname -- network adapter            1024.00
vmname2 -- network adapter              0.00
```

**記錄重點：**
- VM 名稱與網卡名稱之間的分隔符（` -- ` 還是其他）
- 網卡名稱的格式

---

## Step 3：確認 VM 記憶體資訊

```powershell
Get-VM | Select-Object Name, State,
    @{N='MemoryAssignedGB'; E={[math]::Round($_.MemoryAssigned/1GB,2)}},
    @{N='MemoryDemandGB';   E={[math]::Round($_.MemoryDemand/1GB,2)}},
    @{N='MemoryMaximumGB';  E={[math]::Round($_.MemoryMaximum/1GB,2)}},
    DynamicMemoryEnabled |
    Format-Table -AutoSize
```

**記錄重點：**
- `DynamicMemoryEnabled` 欄位值（`True` / `False`）
- 靜態記憶體 VM 的 `MemoryDemandGB` 是否為 0
- `MemoryAssignedGB` 與 `MemoryMaximumGB` 是否相等（靜態 VM 通常相同）

---

## 結果回報格式

請將三個指令的輸出複製貼上，格式如下：

```
=== Step 1 VP 計數器 ===
（貼上輸出）

=== Step 2 網路計數器 ===
（貼上輸出）

=== Step 3 VM 記憶體資訊 ===
（貼上輸出）
```
