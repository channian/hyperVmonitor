from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Host, VM, VMMetric, VMSnapshot, VMReplication, SecurityEvent
from schemas import OverviewResponse, ActionItem, SectionCard

router = APIRouter(prefix="/api/overview", tags=["overview"])


def _cpu_status(pct: float) -> str:
    if pct >= 85:
        return "err"
    if pct >= 70:
        return "warn"
    return "ok"


def _latest_vm_metric(db: Session, vm_id: int) -> VMMetric | None:
    return (
        db.query(VMMetric)
        .filter_by(vm_id=vm_id)
        .order_by(VMMetric.collected_at.desc())
        .first()
    )


def _snapshot_compliance(is_sql: bool, snapshots: list, now: datetime) -> str:
    if not snapshots:
        return "ok"
    if is_sql:
        return "err"
    oldest = min(snapshots, key=lambda s: s.created_at)
    age = (now - oldest.created_at).days
    if age > 7:
        return "err"
    if age > 3:
        return "warn"
    return "ok"


@router.get("", response_model=OverviewResponse)
def get_overview(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    hosts = db.query(Host).all()
    vms = db.query(VM).all()

    # ── 資源視角 ──────────────────────────────────
    resource_warn: list[tuple[VM, VMMetric]] = []
    for vm in vms:
        m = _latest_vm_metric(db, vm.id)
        if m and _cpu_status(m.cpu_pct) != "ok":
            resource_warn.append((vm, m))

    resource_status = (
        "err" if any(_cpu_status(m.cpu_pct) == "err" for _, m in resource_warn)
        else "warn" if resource_warn
        else "ok"
    )

    # ── 快照視角 ──────────────────────────────────
    snap_err = snap_warn = 0
    snap_action_items: list[ActionItem] = []
    for vm in vms:
        snaps = db.query(VMSnapshot).filter_by(vm_id=vm.id).all()
        status = _snapshot_compliance(vm.is_sql, snaps, now)
        if status == "err":
            snap_err += 1
            oldest = min(snaps, key=lambda s: s.created_at) if snaps else None
            age = (now - oldest.created_at).days if oldest else 0
            msg = "SQL Server VM 有快照（即違規）" if vm.is_sql else f"快照已 {age} 天未清理，請儘速刪除"
            snap_action_items.append(ActionItem(severity="err", source=vm.name, message=msg))
        elif status == "warn":
            snap_warn += 1

    snap_status = "err" if snap_err else ("warn" if snap_warn else "ok")

    # ── 複寫 / 備份視角 ───────────────────────────
    repl_err = 0
    repl_action_items: list[ActionItem] = []
    for vm in vms:
        r = (
            db.query(VMReplication)
            .filter_by(vm_id=vm.id)
            .order_by(VMReplication.collected_at.desc())
            .first()
        )
        if r and r.replication_health in ("Critical", "Warning"):
            repl_err += 1
            lag = (
                int((now - r.last_replication_time).total_seconds() / 60)
                if r.last_replication_time
                else 0
            )
            repl_action_items.append(ActionItem(
                severity="err" if r.replication_health == "Critical" else "warn",
                source=vm.name,
                message=f"複寫狀態 {r.replication_health}，落後 {lag} 分鐘",
            ))

    backup_status = "err" if repl_err else "ok"

    # ── 資安視角 ──────────────────────────────────
    sec_today = db.query(SecurityEvent).filter(SecurityEvent.occurred_at >= today_start).all()
    sec_err_count = sum(1 for e in sec_today if e.severity == "err")
    sec_warn_count = sum(1 for e in sec_today if e.severity == "warn")
    sec_status = "err" if sec_err_count else ("warn" if sec_warn_count else "ok")

    sec_action_items: list[ActionItem] = [
        ActionItem(
            severity="err",
            source=e.source_host,
            message=e.description or f"事件 {e.event_id}：{e.account}",
        )
        for e in sec_today if e.severity == "err"
    ][:3]

    # ── 資源警告動作 ──────────────────────────────
    res_action_items: list[ActionItem] = [
        ActionItem(
            severity=_cpu_status(m.cpu_pct),
            source=vm.name,
            message=f"CPU {m.cpu_pct:.0f}%，超過門檻，建議擴增 vCPU（目前 {vm.vcpu} 核）",
        )
        for vm, m in resource_warn
    ][:3]

    # ── 健康度 ────────────────────────────────────
    issue_count = snap_err + repl_err + sec_err_count + len(resource_warn)
    total_checks = max(len(vms) * 4, 1)
    health_pct = max(0, int((1 - issue_count / total_checks) * 100))
    alert_count = snap_err + repl_err + sec_err_count + sum(
        1 for _, m in resource_warn if _cpu_status(m.cpu_pct) == "err"
    )

    snap_ok = len(vms) - snap_err - snap_warn
    has_repl = db.query(VMReplication).first() is not None

    return OverviewResponse(
        host_count=len(hosts),
        vm_count=len(vms),
        alert_count=alert_count,
        snapshot_violation_count=snap_err,
        health_pct=health_pct,
        last_updated=now,
        section_cards=[
            SectionCard(
                id="resources", title="資源監控",
                status=resource_status,
                summary=f"{len(hosts)} 台主機運行中",
                detail=f"{len(resource_warn)} 台 VM 資源超標" if resource_warn else "所有 VM 資源正常",
                counts=[
                    {"label": "實體主機", "v": len(hosts), "k": "ok"},
                    {"label": "警告 VM",  "v": len(resource_warn), "k": resource_status},
                ],
            ),
            SectionCard(
                id="snapshots", title="快照合規",
                status=snap_status,
                summary=f"合規率 {snap_ok} / {len(vms)}",
                detail=f"{snap_err} 台違規・{snap_warn} 台警告" if (snap_err or snap_warn) else "所有 VM 快照合規",
                counts=[
                    {"label": "違規", "v": snap_err,  "k": "err" if snap_err else "ok"},
                    {"label": "合規", "v": snap_ok,   "k": "ok"},
                ],
            ),
            SectionCard(
                id="backup", title="備份 / HA",
                status=backup_status,
                summary=f"複寫異常 {repl_err} 台" if repl_err else "複寫狀態正常",
                detail="無複寫資料（尚未設定）" if not has_repl else (
                    f"{repl_err} 台複寫異常" if repl_err else "所有複寫正常"
                ),
                counts=[{"label": "複寫異常", "v": repl_err, "k": "err" if repl_err else "ok"}],
            ),
            SectionCard(
                id="security", title="資安監控",
                status=sec_status,
                summary=f"今日 {len(sec_today)} 件事件" if sec_today else "今日無安全事件",
                detail=f"嚴重 {sec_err_count} 件・警告 {sec_warn_count} 件" if sec_today else "無事件記錄",
                counts=[
                    {"label": "嚴重", "v": sec_err_count,  "k": "err"  if sec_err_count  else "ok"},
                    {"label": "警告", "v": sec_warn_count, "k": "warn" if sec_warn_count else "ok"},
                ],
            ),
        ],
        action_items=res_action_items + snap_action_items[:3] + repl_action_items + sec_action_items,
    )
