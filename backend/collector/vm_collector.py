"""VM 資源收集器：Get-VM + Get-Counter（每 15 分鐘）"""
import json
from datetime import datetime
from sqlalchemy.orm import Session
from .winrm_client import WinRMClient
from models import VM, VMMetric, Host, HostMetric

# PowerShell：取得所有 VM 基本資訊
# MemoryDemand：Dynamic Memory 啟用時才有意義；關閉時為 0
# MemoryMaximum：VM 設定的最大記憶體（用於計算靜態記憶體壓力）
_PS_GET_VM = """
Get-VM | Select-Object Name, State, ProcessorCount,
    @{N='MemoryAssignedGB';E={[math]::Round($_.MemoryAssigned/1GB,2)}},
    @{N='MemoryDemandGB';E={[math]::Round($_.MemoryDemand/1GB,2)}},
    @{N='MemoryMaximumGB';E={[math]::Round($_.MemoryMaximum/1GB,2)}},
    DynamicMemoryEnabled |
    ConvertTo-Json -Compress
"""

# PowerShell：取得 Hyper-V 效能計數器（CPU / 網路）
# CPU：萬用字元取所有 VP，按 VM 彙整平均（支援多 vCPU）
# 網路：萬用字元取所有網卡，按 VM 加總
_PS_GET_COUNTER = r"""
$cpuMap    = @{}
$netInMap  = @{}
$netOutMap = @{}

# CPU - 所有 VP，instance 格式: "vmname:hv vp N"
$vpSamples = (Get-Counter '\Hyper-V Hypervisor Virtual Processor(*)\% Guest Run Time' `
    -ErrorAction SilentlyContinue).CounterSamples
foreach ($s in $vpSamples) {
    if ($s.InstanceName -notmatch ':hv vp') { continue }
    $vm = ($s.InstanceName -split ':hv vp')[0].ToUpper().Trim()
    if (-not $cpuMap.ContainsKey($vm)) { $cpuMap[$vm] = @() }
    $cpuMap[$vm] += $s.CookedValue
}

# 網路 - instance 格式: "vmname -- adaptername"
$netSamples = (Get-Counter `
    '\Hyper-V Virtual Network Adapter(*)\Bytes Received/sec', `
    '\Hyper-V Virtual Network Adapter(*)\Bytes Sent/sec' `
    -ErrorAction SilentlyContinue).CounterSamples
foreach ($s in $netSamples) {
    $vm = ($s.InstanceName -split ' -- ')[0].ToUpper().Trim()
    if ($s.Path -like '*Received*') {
        $netInMap[$vm]  = [double]($netInMap[$vm])  + $s.CookedValue
    } else {
        $netOutMap[$vm] = [double]($netOutMap[$vm]) + $s.CookedValue
    }
}

$result = Get-VM | Where-Object State -eq 'Running' | ForEach-Object {
    $n    = $_.Name.ToUpper()
    $vals = $cpuMap[$n]
    $cpu  = if ($vals -and $vals.Count -gt 0) {
        [math]::Round(($vals | Measure-Object -Average).Average, 1)
    } else { 0.0 }
    [PSCustomObject]@{
        VM         = $n
        CpuPct     = $cpu
        NetInKBps  = [math]::Round([double]($netInMap[$n])  / 1024, 1)
        NetOutKBps = [math]::Round([double]($netOutMap[$n]) / 1024, 1)
    }
}
$result | ConvertTo-Json -Compress
"""

# PowerShell：取得實體主機 CPU / RAM / 磁碟
_PS_GET_HOST = r"""
$cpu = (Get-Counter '\Processor(_Total)\% Processor Time').CounterSamples[0].CookedValue
$os  = Get-CimInstance Win32_OperatingSystem
$disk = Get-PSDrive C | Select-Object Used, Free
[PSCustomObject]@{
    CpuPct        = [math]::Round($cpu, 1)
    RamUsedGB     = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory)/1MB, 1)
    RamTotalGB    = [math]::Round($os.TotalVisibleMemorySize/1MB, 1)
    DiskUsedGB    = [math]::Round($disk.Used/1GB, 1)
    DiskFreeGB    = [math]::Round($disk.Free/1GB, 1)
} | ConvertTo-Json -Compress
"""


def collect_vm_metrics(client: WinRMClient, db: Session, host_record: Host):
    now = datetime.utcnow()

    # --- 實體主機指標 ---
    host_raw = json.loads(client.run_ps(_PS_GET_HOST))
    db.add(HostMetric(
        host_id=host_record.id,
        cpu_pct=host_raw["CpuPct"],
        ram_used_gb=host_raw["RamUsedGB"],
        ram_total_gb=host_raw["RamTotalGB"],
        storage_used_tb=round(host_raw["DiskUsedGB"] / 1024, 3),
        storage_total_tb=round((host_raw["DiskUsedGB"] + host_raw["DiskFreeGB"]) / 1024, 3),
        collected_at=now,
    ))

    # --- VM 清單同步 ---
    vms_raw = json.loads(client.run_ps(_PS_GET_VM))
    if isinstance(vms_raw, dict):
        vms_raw = [vms_raw]

    vm_map: dict[str, VM] = {}
    for v in vms_raw:
        name = v["Name"].upper()
        vm = db.query(VM).filter_by(name=name).first()
        if vm is None:
            vm = VM(name=name, host_id=host_record.id,
                    vcpu=v["ProcessorCount"], ram_gb=v["MemoryAssignedGB"])
            db.add(vm)
            db.flush()
        vm_map[name] = vm

    # --- 效能計數器 ---
    counters_raw = json.loads(client.run_ps(_PS_GET_COUNTER))
    if isinstance(counters_raw, dict):
        counters_raw = [counters_raw]

    for c in counters_raw:
        name = c["VM"].upper()
        vm = vm_map.get(name)
        if vm is None:
            continue
        vm_obj = db.query(VM).filter_by(name=name).first()
        if vm_obj is None:
            continue
        raw_vm = next((v for v in vms_raw if v["Name"].upper() == name), None)
        ram_assigned = raw_vm["MemoryAssignedGB"] if raw_vm else 0

        # RAM 壓力：
        # - Dynamic Memory 開啟：Demand/Assigned（實際需求 vs 目前配置）
        # - 靜態記憶體：MemoryMaximum == MemoryAssigned，無壓力意義，留 None
        ram_pressure = None
        if raw_vm:
            demand = raw_vm.get("MemoryDemandGB", 0) or 0
            dyn_enabled = raw_vm.get("DynamicMemoryEnabled", False)
            if dyn_enabled and demand > 0 and ram_assigned > 0:
                ram_pressure = round(demand / ram_assigned * 100, 1)

        db.add(VMMetric(
            vm_id=vm_obj.id,
            cpu_pct=c.get("CpuPct", 0),
            ram_used_gb=ram_assigned,
            ram_pressure_pct=ram_pressure,
            net_in_kbps=c.get("NetInKBps", 0),
            net_out_kbps=c.get("NetOutKBps", 0),
            collected_at=now,
        ))

    db.commit()
