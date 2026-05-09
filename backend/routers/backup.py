from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from schemas import BackupResponse, BackupItem, ReplicationItem

router = APIRouter(prefix="/api/backup", tags=["backup"])

_NOW = datetime.utcnow()

_MOCK_BACKUP = [
    BackupItem(vm_name="KHTWXDB",          tier="Tier1", last_backup_time=_NOW.replace(hour=2, minute=0, second=0),          result="Success", result_status="ok",   rpo_met=True,  rpo_label="≤4hr ✅"),
    BackupItem(vm_name="KHTWXAR",          tier="Tier1", last_backup_time=_NOW.replace(hour=2, minute=0, second=0),          result="Success", result_status="ok",   rpo_met=True,  rpo_label="≤4hr ✅"),
    BackupItem(vm_name="KHTWIOTPWR",       tier="Tier1", last_backup_time=(_NOW - timedelta(days=1)).replace(hour=2, minute=0), result="Failed",  result_status="err",  rpo_met=False, rpo_label="超標 ❌"),
    BackupItem(vm_name="KHTWXML",          tier="Tier1", last_backup_time=_NOW.replace(hour=2, minute=30, second=0),         result="Success", result_status="ok",   rpo_met=True,  rpo_label="≤4hr ✅"),
    BackupItem(vm_name="KHTWXFD",          tier="Tier2", last_backup_time=_NOW.replace(hour=3, minute=0, second=0),          result="Success", result_status="ok",   rpo_met=True,  rpo_label="≤24hr ✅"),
    BackupItem(vm_name="KHTWIOTVIB",       tier="Tier2", last_backup_time=_NOW.replace(hour=3, minute=15, second=0),         result="Success", result_status="ok",   rpo_met=True,  rpo_label="≤24hr ✅"),
    BackupItem(vm_name="FACCENTRALJUMP01", tier="Tier2", last_backup_time=_NOW.replace(hour=3, minute=30, second=0),         result="Success", result_status="ok",   rpo_met=True,  rpo_label="≤24hr ✅"),
    BackupItem(vm_name="FACCENTRALJUMP02", tier="Tier2", last_backup_time=_NOW.replace(hour=3, minute=45, second=0),         result="Success", result_status="ok",   rpo_met=True,  rpo_label="≤24hr ✅"),
]

_MOCK_REPLICATION = [
    ReplicationItem(vm_name="KHTWXDB",    replication_state="Normal", replication_health="Normal",   last_replication_time=_NOW - timedelta(minutes=15), lag_minutes=15, rpo_minutes=15, rpo_met=True),
    ReplicationItem(vm_name="KHTWXAR",    replication_state="Normal", replication_health="Normal",   last_replication_time=_NOW - timedelta(minutes=15), lag_minutes=15, rpo_minutes=15, rpo_met=True),
    ReplicationItem(vm_name="KHTWIOTPWR", replication_state="Error",  replication_health="Critical", last_replication_time=_NOW - timedelta(hours=3),    lag_minutes=180, rpo_minutes=15, rpo_met=False),
    ReplicationItem(vm_name="KHTWXML",    replication_state="Normal", replication_health="Normal",   last_replication_time=_NOW - timedelta(minutes=12), lag_minutes=12, rpo_minutes=15, rpo_met=True),
]


@router.get("", response_model=BackupResponse)
def get_backup(db: Session = Depends(get_db)):
    success = sum(1 for b in _MOCK_BACKUP if b.result == "Success")
    return BackupResponse(
        success_count=success,
        total_count=len(_MOCK_BACKUP),
        success_rate_pct=round(success / len(_MOCK_BACKUP) * 100, 1),
        items=_MOCK_BACKUP,
        replication=_MOCK_REPLICATION,
    )
