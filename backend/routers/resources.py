from datetime import datetime, timedelta
import random
from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session
from database import get_db
from schemas import ResourcesResponse, HostSummary, VMSummary, VMDetailResponse, VMHistory

router = APIRouter(prefix="/api/resources", tags=["resources"])

_MOCK_HOSTS = [
    HostSummary(name="KHFACVS01", ip="192.168.1.101", online=True,
                cpu_pct=42, ram_used_gb=312, ram_total_gb=400,
                storage_used_tb=2.8, storage_total_tb=4.0),
    HostSummary(name="KHFACVS02", ip="192.168.1.102", online=True,
                cpu_pct=21, ram_used_gb=220, ram_total_gb=400,
                storage_used_tb=1.2, storage_total_tb=4.0),
]

_MOCK_VMS = [
    VMSummary(name="KHTWXDB",        host="KHFACVS01", vcpu=4,  cpu_pct=90, ram_used_gb=14, ram_pressure_pct=65, net_in_kbps=279,  net_out_kbps=142, state="Running", cpu_status="err",  ram_status="ok"),
    VMSummary(name="KHTWIOTPWR",     host="KHFACVS01", vcpu=4,  cpu_pct=25, ram_used_gb=12, ram_pressure_pct=79, net_in_kbps=21,   net_out_kbps=8,   state="Running", cpu_status="ok",   ram_status="warn"),
    VMSummary(name="KHTWXFD",        host="KHFACVS01", vcpu=4,  cpu_pct=40, ram_used_gb=8,  ram_pressure_pct=None, net_in_kbps=1024, net_out_kbps=512, state="Running", cpu_status="ok", ram_status="ok"),
    VMSummary(name="KHTWXML",        host="KHFACVS01", vcpu=16, cpu_pct=12, ram_used_gb=22, ram_pressure_pct=43, net_in_kbps=2,    net_out_kbps=1,   state="Running", cpu_status="ok",   ram_status="ok"),
    VMSummary(name="KHTWXAR",        host="KHFACVS02", vcpu=4,  cpu_pct=35, ram_used_gb=10, ram_pressure_pct=55, net_in_kbps=50,   net_out_kbps=30,  state="Running", cpu_status="ok",   ram_status="ok"),
    VMSummary(name="KHTWIOTVIB",     host="KHFACVS02", vcpu=2,  cpu_pct=18, ram_used_gb=4,  ram_pressure_pct=30, net_in_kbps=5,    net_out_kbps=2,   state="Running", cpu_status="ok",   ram_status="ok"),
    VMSummary(name="FACCENTRALJUMP01", host="KHFACVS02", vcpu=2, cpu_pct=8, ram_used_gb=4,  ram_pressure_pct=20, net_in_kbps=10,   net_out_kbps=5,   state="Running", cpu_status="ok",   ram_status="ok"),
    VMSummary(name="FACCENTRALJUMP02", host="KHFACVS02", vcpu=2, cpu_pct=7, ram_used_gb=4,  ram_pressure_pct=18, net_in_kbps=8,    net_out_kbps=4,   state="Running", cpu_status="ok",   ram_status="ok"),
]


def _make_history(base_cpu: float, days: int = 7) -> list[VMHistory]:
    now = datetime.utcnow()
    points = []
    for i in range(days * 4):   # 每 6 小時一個點，共 28 點
        t = now - timedelta(hours=(days * 4 - i) * 6)
        jitter = random.uniform(-8, 8)
        points.append(VMHistory(
            collected_at=t,
            cpu_pct=max(0, min(100, base_cpu + jitter)),
            ram_pressure_pct=None,
        ))
    return points


@router.get("", response_model=ResourcesResponse)
def get_resources(db: Session = Depends(get_db)):
    return ResourcesResponse(hosts=_MOCK_HOSTS, vms=_MOCK_VMS)


@router.get("/vms/{vm_name}", response_model=VMDetailResponse)
def get_vm_detail(vm_name: str = Path(...), db: Session = Depends(get_db)):
    vm = next((v for v in _MOCK_VMS if v.name == vm_name), None)
    if vm is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="VM not found")
    history = _make_history(vm.cpu_pct)
    cpu_values = [h.cpu_pct for h in history]
    p95 = sorted(cpu_values)[int(len(cpu_values) * 0.95)]
    avg = sum(cpu_values) / len(cpu_values)
    recommended = int(vm.vcpu * 1.5) if p95 > 85 else None
    return VMDetailResponse(vm=vm, history=history, cpu_p95=round(p95, 1), cpu_avg=round(avg, 1), recommended_vcpu=recommended)
