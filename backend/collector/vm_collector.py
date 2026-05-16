"""VM 資源收集器：Get-VM + Get-Counter（每 15 分鐘）"""
import json
import logging
import os
from datetime import datetime
from sqlalchemy.orm import Session
from .winrm_client import WinRMClient
from models import VM, VMMetric, Host, HostMetric

log = logging.getLogger(__name__)

# vm_credentials.json 路徑（backend/ 目錄下）
_CREDS_FILE = os.path.join(os.path.dirname(__file__), "..", "vm_credentials.json")


def _load_vm_credentials() -> dict[str, dict]:
    """
    載入 vm_credentials.json，格式：
    { "VMNAME": { "user": "...", "password": "..." }, ... }
    VM 名稱統一大寫比對。
    """
    try:
        with open(_CREDS_FILE, encoding="utf-8") as f:
            raw = json.load(f)
        return {k.upper(): v for k, v in raw.items()}
    except FileNotFoundError:
        return {}
    except Exception as e:
        log.warning("載入 vm_credentials.json 失敗：%s", e)
        return {}

_PS_GET_VM = """
Get-VM | Select-Object Name, State, ProcessorCount,
    @{N='MemoryAssignedGB';E={[math]::Round($_.MemoryAssigned/1GB,2)}},
    @{N='MemoryDemandGB';E={[math]::Round($_.MemoryDemand/1GB,2)}},
    DynamicMemoryEnabled |
    ConvertTo-Json -Compress
"""

# CPU：萬用字元取所有 VP，按 VM 彙整平均（支援多 vCPU）
# 網路：繁體中文 Windows instance 格式 vmname_網路介面卡_guid，取底線前部分
_PS_GET_COUNTER = r"""
$cpuMap    = @{}
$netInMap  = @{}
$netOutMap = @{}

$vpSamples = (Get-Counter '\Hyper-V Hypervisor Virtual Processor(*)\% Guest Run Time' `
    -ErrorAction SilentlyContinue).CounterSamples
foreach ($s in $vpSamples) {
    if ($s.InstanceName -notmatch ':hv vp') { continue }
    $vm = ($s.InstanceName -split ':hv vp')[0].ToUpper().Trim()
    if (-not $cpuMap.ContainsKey($vm)) { $cpuMap[$vm] = @() }
    $cpuMap[$vm] += $s.CookedValue
}

$netSamples = (Get-Counter `
    '\Hyper-V Virtual Network Adapter(*)\Bytes Received/sec', `
    '\Hyper-V Virtual Network Adapter(*)\Bytes Sent/sec' `
    -ErrorAction SilentlyContinue).CounterSamples
foreach ($s in $netSamples) {
    $vm = ($s.InstanceName -split '_')[0].ToUpper().Trim()
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

# 取 VM IPv4（IS 有無都能取得，用於 fallback 直連）
_PS_GET_VM_IPS = """
Get-VMNetworkAdapter -VMName * |
    ForEach-Object {
        $ip = ($_.IPAddresses | Where-Object { $_ -match '^\\d+\\.\\d+\\.\\d+\\.\\d+$' })[0]
        if ($ip) {
            [PSCustomObject]@{ VMName = $_.VMName.ToUpper(); IP = $ip }
        }
    } | ConvertTo-Json -Compress
"""

# 直連 VM Guest OS 取實際記憶體用量（IS 無法回報時的 fallback）
_PS_GET_GUEST_RAM = r"""
$os = Get-CimInstance Win32_OperatingSystem
[PSCustomObject]@{
    UsedGB  = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory)/1MB, 2)
    TotalGB = [math]::Round($os.TotalVisibleMemorySize/1MB, 2)
} | ConvertTo-Json -Compress
"""


def _get_vm_ips(client: WinRMClient) -> dict[str, str]:
    """取得宿主機上各 VM 的第一個 IPv4，回傳 {VM名稱大寫: IP}。"""
    try:
        raw = client.run_ps(_PS_GET_VM_IPS).strip()
        if not raw or raw == "null":
            return {}
        items = json.loads(raw)
        if isinstance(items, dict):
            items = [items]
        return {item["VMName"]: item["IP"] for item in items if item.get("IP")}
    except Exception as e:
        log.warning("取得 VM IP 失敗：%s", e)
        return {}


def _get_guest_ram_pressure(
    vm_name: str,
    vm_ip: str,
    ram_assigned_gb: float,
    vm_creds: dict[str, dict],
    default_user: str = "",
    default_password: str = "",
) -> float | None:
    """直連 VM 取 Guest OS 記憶體用量，回傳壓力百分比。失敗回傳 None。"""
    cred = vm_creds.get(vm_name, {})
    user = cred.get("user") or default_user
    password = cred.get("password") or default_password
    if not user or not password:
        log.debug("VM %s 無可用帳密，跳過直連", vm_name)
        return None
    try:
        guest = WinRMClient(vm_ip, user, password)
        raw = json.loads(guest.run_ps(_PS_GET_GUEST_RAM))
        used = raw.get("UsedGB", 0)
        if used > 0 and ram_assigned_gb > 0:
            return round(used / ram_assigned_gb * 100, 1)
    except Exception as e:
        log.debug("VM %s 直連取 RAM 失敗：%s", vm_name, e)
    return None


def collect_vm_metrics(
    client: WinRMClient,
    db: Session,
    host_record: Host,
    winrm_user: str = "",
    winrm_password: str = "",
):
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
        else:
            # 同步最新 vCPU / RAM 配置
            vm.vcpu = v["ProcessorCount"]
            vm.ram_gb = v["MemoryAssignedGB"]
            vm.state = v.get("State", vm.state)
        vm_map[name] = vm

    # --- 載入 VM 個別帳密 + 取 VM IP ---
    vm_creds = _load_vm_credentials()
    vm_ips = _get_vm_ips(client)

    # --- 效能計數器 ---
    counters_raw = json.loads(client.run_ps(_PS_GET_COUNTER))
    if isinstance(counters_raw, dict):
        counters_raw = [counters_raw]

    for c in counters_raw:
        name = c["VM"].upper()
        vm_obj = vm_map.get(name)
        if vm_obj is None:
            continue

        raw_vm = next((v for v in vms_raw if v["Name"].upper() == name), None)
        ram_assigned = raw_vm["MemoryAssignedGB"] if raw_vm else 0

        # RAM 壓力計算：
        # 1. MemoryDemand > 0 → IS 正常回報，直接用 Demand/Assigned
        # 2. MemoryDemand = 0 → IS 無法回報，fallback 直連 VM 取 Guest OS 用量
        ram_pressure = None
        if raw_vm:
            demand = raw_vm.get("MemoryDemandGB", 0) or 0
            if demand > 0 and ram_assigned > 0:
                ram_pressure = round(demand / ram_assigned * 100, 1)
            elif demand == 0:
                vm_ip = vm_ips.get(name)
                if vm_ip:
                    ram_pressure = _get_guest_ram_pressure(
                        name, vm_ip, ram_assigned, vm_creds,
                        default_user=winrm_user, default_password=winrm_password,
                    )
                    if ram_pressure is not None:
                        log.info("VM %s 透過直連取得 RAM 壓力：%.1f%%", name, ram_pressure)

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
