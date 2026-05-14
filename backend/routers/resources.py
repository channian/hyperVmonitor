from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Path, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Host, HostMetric, VM, VMMetric
from schemas import ResourcesResponse, HostSummary, VMSummary, VMDetailResponse, VMHistory

router = APIRouter(prefix="/api/resources", tags=["resources"])


def _cpu_status(pct: float) -> str:
    if pct >= 85:
        return "err"
    if pct >= 70:
        return "warn"
    return "ok"


def _ram_status(pct: float | None) -> str:
    if pct is None:
        return "ok"
    if pct >= 80:
        return "err"
    if pct >= 70:
        return "warn"
    return "ok"


def _latest_host_metric(db: Session, host_id: int) -> HostMetric | None:
    return (
        db.query(HostMetric)
        .filter_by(host_id=host_id)
        .order_by(HostMetric.collected_at.desc())
        .first()
    )


def _latest_vm_metric(db: Session, vm_id: int) -> VMMetric | None:
    return (
        db.query(VMMetric)
        .filter_by(vm_id=vm_id)
        .order_by(VMMetric.collected_at.desc())
        .first()
    )


def _build_vm_summary(vm: VM, m: VMMetric | None) -> VMSummary:
    cpu = round(m.cpu_pct, 1) if m else 0.0
    ram_used = round(m.ram_used_gb, 1) if m else 0.0
    ram_pres = round(m.ram_pressure_pct, 1) if (m and m.ram_pressure_pct is not None) else None
    net_in  = round(m.net_in_kbps, 1) if m else 0.0
    net_out = round(m.net_out_kbps, 1) if m else 0.0
    return VMSummary(
        name=vm.name,
        host=vm.host.name,
        vcpu=vm.vcpu,
        cpu_pct=cpu,
        ram_used_gb=ram_used,
        ram_pressure_pct=ram_pres,
        net_in_kbps=net_in,
        net_out_kbps=net_out,
        state=vm.state,
        cpu_status=_cpu_status(cpu),
        ram_status=_ram_status(ram_pres),
    )


@router.get("", response_model=ResourcesResponse)
def get_resources(db: Session = Depends(get_db)):
    hosts = db.query(Host).all()
    host_summaries = []
    for h in hosts:
        m = _latest_host_metric(db, h.id)
        host_summaries.append(HostSummary(
            name=h.name,
            ip=h.ip,
            online=h.online,
            cpu_pct=round(m.cpu_pct, 1) if m else 0.0,
            ram_used_gb=round(m.ram_used_gb, 1) if m else 0.0,
            ram_total_gb=round(m.ram_total_gb, 1) if m else 0.0,
            storage_used_tb=round(m.storage_used_tb, 2) if m else 0.0,
            storage_total_tb=round(m.storage_total_tb, 2) if m else 0.0,
        ))

    vms = db.query(VM).all()
    vm_summaries = [_build_vm_summary(vm, _latest_vm_metric(db, vm.id)) for vm in vms]

    return ResourcesResponse(hosts=host_summaries, vms=vm_summaries)


@router.get("/vms/{vm_name}", response_model=VMDetailResponse)
def get_vm_detail(vm_name: str = Path(...), db: Session = Depends(get_db)):
    vm = db.query(VM).filter(VM.name == vm_name.upper()).first()
    if vm is None:
        raise HTTPException(status_code=404, detail="VM not found")

    since = datetime.utcnow() - timedelta(days=7)
    metrics = (
        db.query(VMMetric)
        .filter(VMMetric.vm_id == vm.id, VMMetric.collected_at >= since)
        .order_by(VMMetric.collected_at.asc())
        .all()
    )

    history = [
        VMHistory(
            collected_at=m.collected_at,
            cpu_pct=round(m.cpu_pct, 1),
            ram_pressure_pct=round(m.ram_pressure_pct, 1) if m.ram_pressure_pct is not None else None,
        )
        for m in metrics
    ]

    latest = _latest_vm_metric(db, vm.id)
    cpu_values = [m.cpu_pct for m in metrics] if metrics else ([latest.cpu_pct] if latest else [0.0])
    p95 = sorted(cpu_values)[int(len(cpu_values) * 0.95)]
    avg = sum(cpu_values) / len(cpu_values)
    recommended_vcpu = int(vm.vcpu * 1.5) if p95 > 85 else None

    return VMDetailResponse(
        vm=_build_vm_summary(vm, latest),
        history=history,
        cpu_p95=round(p95, 1),
        cpu_avg=round(avg, 1),
        recommended_vcpu=recommended_vcpu,
    )
