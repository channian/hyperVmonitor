from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import VM, VMReplication, BackupJob
from schemas import BackupResponse, BackupItem, ReplicationItem

router = APIRouter(prefix="/api/backup", tags=["backup"])

_RPO_HOURS = {"Tier1": 4, "Tier2": 24}


@router.get("", response_model=BackupResponse)
def get_backup(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    vms = db.query(VM).all()

    # ── 複寫（真實資料）──────────────────────────
    replication_items: list[ReplicationItem] = []
    for vm in vms:
        r = (
            db.query(VMReplication)
            .filter_by(vm_id=vm.id)
            .order_by(VMReplication.collected_at.desc())
            .first()
        )
        if r is None:
            continue
        lag = (
            int((now - r.last_replication_time).total_seconds() / 60)
            if r.last_replication_time
            else 0
        )
        replication_items.append(ReplicationItem(
            vm_name=vm.name,
            replication_state=r.replication_state,
            replication_health=r.replication_health,
            last_replication_time=r.last_replication_time,
            lag_minutes=lag,
            rpo_minutes=r.rpo_minutes,
            rpo_met=lag <= r.rpo_minutes,
        ))

    # ── 備份 Job（Veeam 整合前：有資料就顯示，無資料顯示 NoData）──
    backup_items: list[BackupItem] = []
    for vm in vms:
        j = (
            db.query(BackupJob)
            .filter_by(vm_id=vm.id)
            .order_by(BackupJob.start_time.desc())
            .first()
        )
        rpo_hours = _RPO_HOURS.get(vm.tier, 24)

        if j is None:
            backup_items.append(BackupItem(
                vm_name=vm.name,
                tier=vm.tier,
                last_backup_time=None,
                result="NoData",
                result_status="warn",
                rpo_met=False,
                rpo_label="無資料",
            ))
        else:
            age_hours = (now - j.start_time).total_seconds() / 3600
            rpo_met = j.result == "Success" and age_hours <= rpo_hours
            result_status = "ok" if j.result == "Success" else ("warn" if j.result == "Warning" else "err")
            backup_items.append(BackupItem(
                vm_name=vm.name,
                tier=vm.tier,
                last_backup_time=j.start_time,
                result=j.result,
                result_status=result_status,
                rpo_met=rpo_met,
                rpo_label=f"≤{rpo_hours}hr {'✅' if rpo_met else '❌'}",
            ))

    success = sum(1 for b in backup_items if b.result == "Success")
    total = len(backup_items)
    return BackupResponse(
        success_count=success,
        total_count=total,
        success_rate_pct=round(success / total * 100, 1) if total else 0.0,
        items=sorted(backup_items, key=lambda x: x.tier),
        replication=replication_items,
    )
