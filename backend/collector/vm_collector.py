"""VM 資源收集器：Get-VM + Get-Counter（每 15 分鐘）"""
import json
from datetime import datetime
from sqlalchemy.orm import Session
from .winrm_client import WinRMClient
from models import VM, VMMetric, Host, HostMetric

# PowerShell：取得所有 VM 基本資訊
_PS_GET_VM = """
Get-VM | Select-Object Name, State, ProcessorCount,
    @{N='MemoryAssignedGB';E={[math]::Round($_.MemoryAssigned/1GB,2)}},
    @{N='MemoryDemandGB';E={[math]::Round($_.MemoryDemand/1GB,2)}} |
    ConvertTo-Json -Compress
"""

# PowerShell：取得 Hyper-V 效能計數器（CPU / 網路）
_PS_GET_COUNTER = r"""
$vms = Get-VM | Where-Object State -eq 'Running' | Select-Object -ExpandProperty Name
$result = foreach ($vm in $vms) {
    $cpuPath  = "\Hyper-V Hypervisor Virtual Processor($vm:Hv VP 0)\% Guest Run Time"
    $netInPath  = "\Hyper-V Virtual Network Adapter($vm - $vm)\Bytes Received/sec"
    $netOutPath = "\Hyper-V Virtual Network Adapter($vm - $vm)\Bytes Sent/sec"
    $counters = @($cpuPath, $netInPath, $netOutPath)
    $raw = Get-Counter -Counter $counters -ErrorAction SilentlyContinue
    [PSCustomObject]@{
        VM       = $vm
        CpuPct   = [math]::Round(($raw.CounterSamples | Where-Object Path -like "*Guest Run Time*").CookedValue, 1)
        NetInKBps = [math]::Round(($raw.CounterSamples | Where-Object Path -like "*Bytes Received*").CookedValue / 1024, 1)
        NetOutKBps= [math]::Round(($raw.CounterSamples | Where-Object Path -like "*Bytes Sent*").CookedValue / 1024, 1)
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
        ram_pressure = None
        if vm_obj.ram_gb:
            raw_vm = next((v for v in vms_raw if v["Name"].upper() == name), None)
            if raw_vm and raw_vm.get("MemoryDemandGB"):
                ram_pressure = round(raw_vm["MemoryDemandGB"] / vm_obj.ram_gb * 100, 1)

        db.add(VMMetric(
            vm_id=vm_obj.id,
            cpu_pct=c.get("CpuPct", 0),
            ram_used_gb=raw_vm["MemoryAssignedGB"] if raw_vm else 0,
            ram_pressure_pct=ram_pressure,
            net_in_kbps=c.get("NetInKBps", 0),
            net_out_kbps=c.get("NetOutKBps", 0),
            collected_at=now,
        ))

    db.commit()
