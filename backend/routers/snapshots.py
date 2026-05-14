from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import VM, VMSnapshot
from schemas import SnapshotResponse, SnapshotItem

router = APIRouter(prefix="/api/snapshots", tags=["snapshots"])


def _compliance(is_sql: bool, age_days: int, has_snapshots: bool) -> tuple[str, str]:
    """Returns (status, label)。遵循 CLAUDE.md 快照合規規則。"""
    if not has_snapshots:
        return "ok", "合規"
    if is_sql:
        return "err", "嚴重違規"
    if age_days > 7:
        return "err", "違規"
    if age_days > 3:
        return "warn", "警告"
    return "ok", "合規"


@router.get("", response_model=SnapshotResponse)
def get_snapshots(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    vms = db.query(VM).all()
    items: list[SnapshotItem] = []

    for vm in vms:
        snapshots = db.query(VMSnapshot).filter_by(vm_id=vm.id).all()

        if not snapshots:
            status, label = _compliance(vm.is_sql, 0, False)
            items.append(SnapshotItem(
                vm_name=vm.name,
                snapshot_count=0,
                oldest_snapshot_date=None,
                age_days=0,
                compliance_status=status,
                compliance_label=label,
                is_sql=vm.is_sql,
            ))
            continue

        oldest = min(snapshots, key=lambda s: s.created_at)
        age_days = (now - oldest.created_at).days
        status, label = _compliance(vm.is_sql, age_days, True)
        items.append(SnapshotItem(
            vm_name=vm.name,
            snapshot_count=len(snapshots),
            oldest_snapshot_date=oldest.created_at,
            age_days=age_days,
            compliance_status=status,
            compliance_label=label,
            is_sql=vm.is_sql,
        ))

    violations = [s for s in items if s.compliance_status != "ok"]
    compliant  = [s for s in items if s.compliance_status == "ok"]
    return SnapshotResponse(
        compliance_count=len(compliant),
        violation_count=len(violations),
        total_count=len(items),
        items=sorted(items, key=lambda x: x.age_days, reverse=True),
    )
