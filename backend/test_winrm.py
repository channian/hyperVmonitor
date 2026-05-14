"""
WinRM 連線測試腳本。
確認 Python 能透過 pywinrm 連上 Hyper-V 宿主機並執行 PowerShell 指令。

用法：
    cd backend
    python test_winrm.py

設定從 backend/.env 自動讀取（HV_HOSTS / WINRM_USER / WINRM_PASSWORD）。
"""
import json
import sys

sys.path.insert(0, ".")

# 透過 pydantic-settings 讀取 .env，與 FastAPI / scheduler 共用同一份設定
from database import settings  # noqa: E402

HOST     = settings.hv_hosts.split(",")[0].strip() if settings.hv_hosts else "192.168.1.101"
USER     = settings.winrm_user
PASSWORD = settings.winrm_password
# ────────────────────────────────────────────────────────────

try:
    from collector.winrm_client import WinRMClient
except ImportError as e:
    print(f"[ERROR] 無法匯入 WinRMClient：{e}")
    print("請確認在 backend/ 目錄下執行，且已安裝 pywinrm")
    sys.exit(1)

PASS = "✅"
FAIL = "❌"
WARN = "⚠️"

results: list[tuple[str, bool, str]] = []


def run_test(label: str, script: str, parse_json: bool = True) -> bool:
    print(f"\n{'─'*55}")
    print(f"  測試：{label}")
    print(f"{'─'*55}")
    try:
        raw = client.run_ps(script)
        if not raw.strip():
            print(f"{WARN} 回傳空字串（可能此主機無相關資料）")
            results.append((label, True, "空回傳"))
            return True

        if parse_json:
            data = json.loads(raw)
            # PowerShell 單筆回傳 dict，多筆回傳 list
            if isinstance(data, dict):
                data = [data]
            print(f"{PASS} 成功，回傳 {len(data)} 筆")
            for item in data[:3]:
                # 只印關鍵欄位，避免輸出太長
                if isinstance(item, dict):
                    brief = {k: v for i, (k, v) in enumerate(item.items()) if i < 5}
                    print(f"   {brief}")
                else:
                    print(f"   {item}")
            results.append((label, True, f"{len(data)} 筆"))
        else:
            print(f"{PASS} 成功")
            print(f"   {raw.strip()[:200]}")
            results.append((label, True, "OK"))
        return True

    except json.JSONDecodeError:
        # 不是 JSON 也可能是正常純文字輸出（如計數器測試）
        print(f"{WARN} 非 JSON 回應（可視為正常）")
        print(f"   {raw.strip()[:300]}")
        results.append((label, True, "非JSON回應"))
        return True
    except Exception as e:
        print(f"{FAIL} 失敗：{e}")
        results.append((label, False, str(e)[:120]))
        return False


# ── 建立連線 ───────────────────────────────────────────────
print(f"\n{'='*55}")
print(f"  Hyper-V WinRM 連線測試")
print(f"  目標主機：{HOST}")
print(f"  帳號：    {USER}")
print(f"{'='*55}")

try:
    client = WinRMClient(HOST, USER, PASSWORD)
    print(f"{PASS} WinRMClient 初始化完成")
except Exception as e:
    print(f"{FAIL} 無法建立 WinRMClient：{e}")
    sys.exit(1)

# ── 測試 1：基本連線（whoami）─────────────────────────────
run_test(
    "基本連線 (whoami)",
    "whoami",
    parse_json=False,
)

# ── 測試 2：Get-VM 基本資訊 ───────────────────────────────
run_test(
    "Get-VM 基本資訊",
    "Get-VM | Select-Object Name, State, ProcessorCount, MemoryAssigned | ConvertTo-Json -Compress",
)

# ── 測試 3：Get-VMSnapshot 快照清單 ───────────────────────
run_test(
    "Get-VMSnapshot 快照清單",
    "Get-VMSnapshot -VMName * | Select-Object VMName, Name, CreationTime | ConvertTo-Json -Compress",
)

# ── 測試 4：Get-VMReplication 複寫狀態 ───────────────────
run_test(
    "Get-VMReplication 複寫狀態",
    "Get-VMReplication | Select-Object VMName, State, Health, ReplicationFrequencySec | ConvertTo-Json -Compress",
)

# ── 測試 5：Hyper-V 超管理程式計數器 ─────────────────────
run_test(
    "Hyper-V 超管理程式計數器 (Virtual Processors)",
    r"(Get-Counter '\Hyper-V Hypervisor\Virtual Processors' -ErrorAction SilentlyContinue).CounterSamples "
    r"| Select-Object Path, CookedValue | ConvertTo-Json -Compress",
)

# ── 測試 6：宿主機 CPU 計數器 ─────────────────────────────
run_test(
    "宿主機 CPU 使用率計數器",
    r"(Get-Counter '\Processor(_Total)\% Processor Time').CounterSamples "
    r"| Select-Object Path, CookedValue | ConvertTo-Json -Compress",
)

# ── 測試 7：Windows 事件記錄（安全性事件）────────────────
run_test(
    "安全性事件記錄 (最近 10 筆 EventID 4624/4625)",
    r"""
Get-WinEvent -FilterHashtable @{
    LogName   = 'Security'
    Id        = 4624,4625
    StartTime = (Get-Date).AddMinutes(-30)
} -MaxEvents 10 -ErrorAction SilentlyContinue |
Select-Object Id, TimeCreated, Message |
ConvertTo-Json -Compress
""",
)

# ── 測試 8：Get-VMNetworkAdapter ──────────────────────────
run_test(
    "Get-VMNetworkAdapter 網路卡資訊",
    "Get-VMNetworkAdapter -VMName * | Select-Object VMName, SwitchName, IPAddresses | ConvertTo-Json -Compress",
)

# ── 彙整結果 ──────────────────────────────────────────────
print(f"\n{'='*55}")
print(f"  測試結果彙整")
print(f"{'='*55}")
pass_count = sum(1 for _, ok, _ in results if ok)
fail_count = len(results) - pass_count
for label, ok, detail in results:
    icon = PASS if ok else FAIL
    print(f"  {icon}  {label:<35}  {detail}")

print(f"\n  共 {len(results)} 項測試，通過 {pass_count}，失敗 {fail_count}")
if fail_count == 0:
    print(f"\n  {PASS} 全部通過！可以執行排程收集器了。")
    print(f"     python -m collector.scheduler")
else:
    print(f"\n  {WARN} 有 {fail_count} 項失敗，請依上方錯誤訊息排查。")
    print(f"     參考：docs/winrm-test-guide.md")
print()
